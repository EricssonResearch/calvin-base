# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty, COMMIT_RESPONSE
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)

class FanoutFIFO(object):

    """
    A FIFO with fanout support
    Parameters:
        length is the number of entries in the FIFO
        readers is a set of peer port ids reading from the FIFO
    """

    def __init__(self, port_properties, peer_port_properties):
        super(FanoutFIFO, self).__init__()
        # Set default queue length to 4 if not specified
        length = port_properties.get('queue_length', 4)
        # Compensate length for FIFO having an unused slot
        length += 1
        self.fifo = [Token(0)] * length
        self.N = length
        self.direction = port_properties.get('direction', None)
        self.nbr_peers = port_properties.get('nbr_peers', 1)
        self.readers = set()
        # NOTE: For simplicity, modulo operation is only used in fifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = 0
        self.read_pos = {}
        self.tentative_read_pos = {}
        self.reader_offset = {}
        self._type = "fanout_fifo"
        self.writer = None  # Not part of state, assumed not needed in migrated information

    def __str__(self):
        return "Tokens: %s, w:%i, r:%s, tr:%s" % (self.fifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self, remap=None):
        if remap is None:
            state = {
                'queuetype': self._type,
                'fifo': [t.encode() for t in self.fifo],
                'N': self.N,
                'readers': list(self.readers),
                'write_pos': self.write_pos,
                'read_pos': self.read_pos,
                'tentative_read_pos': self.tentative_read_pos,
                'reader_offset': self.reader_offset
            }
        else:
            # Remapping of port ids, also implies reset of tokens
            state = {
                'queuetype': self._type,
                'fifo': [Token(0).encode()] * len(self.fifo),
                'N': self.N,
                'readers': [remap[pid] if pid in remap else pid for pid in self.readers],
                'write_pos': 0,
                'read_pos': {remap[pid] if pid in remap else pid: 0 for pid, pos in self.read_pos.items()},
                'tentative_read_pos': {remap[pid] if pid in remap else pid: 0 for pid, pos in self.tentative_read_pos.items()},
                'reader_offset': {remap[pid] if pid in remap else pid: 0 for pid, pos in self.reader_offset.items()}
            }
        return state

    def _set_state(self, state):
        self._type = state.get('queuetype',"fanout_fifo")
        self.fifo = [Token.decode(d) for d in state['fifo']]
        self.N = state['N']
        self.readers = set(state['readers'])
        self.write_pos = state['write_pos']
        self.read_pos = state['read_pos']
        self.tentative_read_pos = state['tentative_read_pos']
        self.reader_offset = state.get('reader_offset', {pid: 0 for pid in self.readers})

    @property
    def queue_type(self):
        return self._type

    def add_writer(self, writer, properties):
        self.writer = writer

    def remove_writer(self, writer):
        pass

    def add_reader(self, reader, properties):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        if reader not in self.readers:
            self.readers.add(reader)
            if len(self.readers) > self.nbr_peers:
                self.nbr_peers = len(self.readers)
                # Replicated actor connect for first time, start from oldest possible
                oldest = min(self.read_pos.values())
                #_log.info("ADD_READER %s %s %d" % (reader, str(id(self)), oldest))
                self.reader_offset[reader] = oldest
                self.read_pos[reader] = oldest
                self.tentative_read_pos[reader] = oldest
            else:
                self.reader_offset[reader] = 0
                self.read_pos[reader] = 0
                self.tentative_read_pos[reader] = 0

    def remove_reader(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        del self.read_pos[reader]
        del self.tentative_read_pos[reader]
        del self.reader_offset[reader]
        self.readers.discard(reader)
        self.nbr_peers -= 1

    def get_peers(self):
        if self.direction == "out":
            return self.readers
        elif self.direction == "in" and self.writer is not None:
            return set([self.writer])
        else:
            return None

    def write(self, data, metadata):
        if not self.slots_available(1, metadata):
            raise QueueFull()
        write_pos = self.write_pos
        self.fifo[write_pos % self.N] = data
        self.write_pos = write_pos + 1
        return True

    def slots_available(self, length, metadata):
        last_readpos = min(self.read_pos.values() or [0])
        return (self.N - ((self.write_pos - last_readpos) % self.N) - 1) >= length

    def tokens_available(self, length, metadata):
        if metadata is None and len(self.readers) == 1:
            # we only have one reader for in port queues (the own port id)
            # TODO create seperate FIFO without fanout possibility instead
            metadata = next(iter(self.readers))
        if not isinstance(metadata, basestring):
            raise Exception('Not a string: %s' % metadata)
        if metadata not in self.readers:
            raise Exception("No reader %s in %s" % (metadata, self.readers))
        return (self.write_pos - self.tentative_read_pos[metadata]) >= length

    #
    # Reading is done tentatively until committed
    #
    def peek(self, metadata=None):
        if metadata is None and len(self.readers) == 1:
            # we only have one reader for in port queues (the own port id)
            # TODO create seperate FIFO without fanout possibility instead
            metadata = next(iter(self.readers))
        if not isinstance(metadata, basestring):
            raise Exception('Not a string: %s' % metadata)
        if metadata not in self.readers:
            raise Exception("Unknown reader: '%s'" % metadata)
        if not self.tokens_available(1, metadata):
            raise QueueEmpty(reader=metadata)
        read_pos = self.tentative_read_pos[metadata]
        data = self.fifo[read_pos % self.N]
        self.tentative_read_pos[metadata] = read_pos + 1
        return data

    def commit(self, metadata=None):
        if metadata is None and len(self.readers) == 1:
            # we only have one reader for in port queues (the own port id)
            # TODO create seperate FIFO without fanout possibility instead
            metadata = next(iter(self.readers))
        self.read_pos[metadata] = self.tentative_read_pos[metadata]

    def cancel(self, metadata=None):
        if metadata is None and len(self.readers) == 1:
            # we only have one reader for in port queues (the own port id)
            # TODO create seperate FIFO without fanout possibility instead
            metadata = next(iter(self.readers))
        self.tentative_read_pos[metadata] = self.read_pos[metadata]

    #
    # Queue operations used by communication which utilize a sequence number
    #

    def com_write(self, data, metadata, sequence_nbr):
        if sequence_nbr == self.write_pos:
            self.write(data, metadata)
            return COMMIT_RESPONSE.handled
        elif sequence_nbr < self.write_pos:
            return COMMIT_RESPONSE.unhandled
        else:
            return COMMIT_RESPONSE.invalid

    def com_peek(self, metadata=None):
        pos = self.tentative_read_pos[metadata]
        return (pos - self.reader_offset[metadata], self.peek(metadata))

    def com_commit(self, reader, sequence_nbr):
        """ Will commit one token when the sequence_nbr matches
            return COMMIT_RESPONSE for action on token sequence_nbr.
            Only act on sequence nbrs at end of queue.
            reader: peer_id
            sequence_nbr: token sequence_nbr
        """
        sequence_nbr += self.reader_offset[reader]
        if sequence_nbr >= self.tentative_read_pos[reader]:
            return COMMIT_RESPONSE.invalid
        if self.read_pos[reader] < self.tentative_read_pos[reader]:
            if sequence_nbr == self.read_pos[reader]:
                self.read_pos[reader] += 1
                return COMMIT_RESPONSE.handled
            else:
                return COMMIT_RESPONSE.unhandled

    def com_cancel(self, reader, sequence_nbr):
        """ Will cancel tokens from the sequence_nbr to end
            return COMMIT_RESPONSE for action on tokens.
            reader: peer_id
            sequence_nbr: token sequence_nbr
        """
        sequence_nbr += self.reader_offset[reader]
        if (sequence_nbr >= self.tentative_read_pos[reader] and
            sequence_nbr < self.reader_pos[reader]):
            return COMMIT_RESPONSE.invalid
        self.tentative_read_pos[reader] = sequence_nbr
        return COMMIT_RESPONSE.handled

    def com_is_committed(self, reader):
        return self.tentative_read_pos[reader] == self.read_pos[reader]

