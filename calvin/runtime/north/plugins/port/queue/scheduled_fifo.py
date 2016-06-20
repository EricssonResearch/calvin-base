# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

import random
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty, COMMIT_RESPONSE
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


class ScheduledFIFO(object):

    """
    A FIFO which route tokens based on a schedule to peers
    Parameters:
        port_properties: dictionary must contain key 'routing' with
                         value 'round-robin' or 'random'
    """

    def __init__(self, port_properties):
        super(ScheduledFIFO, self).__init__()
        # Set default queue length to 4 if not specified
        try:
            length = port_properties.get('queue_length', 4)
        except:
            length = 4
        # Compensate length for FIFO having an unused slot
        length += 1
        # Each peer have it's own FIFO
        self.fifo = {}
        try:
            self.nbr_peers = port_properties['nbr_peers']
        except:
            self.nbr_peers = 1
        self.N = length
        # Peers ordered by id
        self.readers = []
        # NOTE: For simplicity, modulo operation is only used in fifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = {}
        self.read_pos = {}
        self.tentative_read_pos = {}
        self.reader_turn = None
        self.turn_pos = 0
        self._type = "scheduled_fifo:" + port_properties['routing']
        self._set_turn()

    def _set_turn(self):
        # Get routing schedule based on info after ':' in type
        # Set the correct method
        routing = self._type.split(':',1)[1]
        if routing == "round-robin":
            self._update_turn = self._round_robin
            if self.reader_turn is None:
                # Populate with alternating values up to N
                self.reader_turn = [p for n in range(self.N) for p in range(self.nbr_peers)][:self.N]
        elif routing == "random":
            self._update_turn = self._random
            if self.reader_turn is None:
                # Populate with random values up to N
                self.reader_turn = [random.randrange(self.nbr_peers) for n in range(self.N)]
        else:
            raise Exception("UNKNOWN QUEUE TYPE" + routing)

    def _round_robin(self):
        reader = self.reader_turn[self.turn_pos % self.N]
        prev = self.reader_turn[(self.turn_pos - 1) % self.N]
        self.reader_turn[self.turn_pos % self.N] = (prev + 1) % self.nbr_peers
        self.turn_pos += 1
        return reader

    def _random(self):
        reader = self.reader_turn[self.turn_pos % self.N]
        self.reader_turn[self.turn_pos % self.N] = random.randrange(self.nbr_peers)
        self.turn_pos += 1
        return reader

    def __str__(self):
        fifo = "\n".join([str(k) + ": " + ", ".join(map(lambda x: str(x), self.fifo[k])) for k in self.fifo.keys()])
        return "Tokens: %s\nw:%s, r:%s, tr:%s" % (fifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self):
        state = {
            'queuetype': self._type,
            'fifo': {p: [t.encode() for t in self.fifo] for p, t in self.fifo.items()},
            'N': self.N,
            'readers': self.readers,
            'write_pos': self.write_pos,
            'read_pos': self.read_pos,
            'tentative_read_pos': self.tentative_read_pos,
            'reader_turn': self.reader_turn,
            'turn_pos': self.turn_pos
        }
        return state

    def _set_state(self, state):
        self._type = state.get('queuetype')
        self.fifo = {p: [Token.decode(t) for t in self.fifo] for p, t in state['fifo'].items()}
        self.N = state['N']
        self.readers = state['readers']
        self.write_pos = state['write_pos']
        self.read_pos = state['read_pos']
        self.tentative_read_pos = state['tentative_read_pos']
        self.token_state = state['token_state']
        self.reader_turn = state["reader_turn"]
        self.turn_pos = state["turn_pos"]
        self._set_turn()

    @property
    def queue_type(self):
        return self._type

    def add_reader(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        if reader not in self.readers:
            self.read_pos[reader] = 0
            self.write_pos[reader] = 0
            self.tentative_read_pos[reader] = 0
            self.fifo.setdefault(reader, [Token(0)] * self.N)
            self.readers.append(reader)
            self.readers.sort()

    def remove_reader(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        del self.read_pos[reader]
        del self.tentative_read_pos[reader]
        del self.write_pos[reader]
        self.readers.remove(reader)

    def write(self, data):
        if not self.slots_available(1):
            raise QueueFull()
        _log.debug("WRITING pos %s" % str(self.write_pos))
        # Write token in peer's FIFO
        peer = self.readers[self._update_turn()]
        write_pos = self.write_pos[peer]
        self.fifo[peer][write_pos % self.N] = data
        self.write_pos[peer] = write_pos + 1
        return True

    def slots_available(self, length):
        if length >= self.N:
            return False
        if length == 1:
            # shortcut for common special case
            peer = self.readers[self.reader_turn[self.turn_pos % self.N]]
            return self.write_pos[peer] - self.read_pos[peer] < self.N - 1
        # list of peer indexes that will be written to
        peers = [self.reader_turn[i % self.N] for i in range(self.turn_pos, self.turn_pos + length)]
        for p in peers:
            # How many slots for this peer
            c = peers.count(p)
            peer = self.readers[p]
            # If this peer does not have c slots then return False
            if (self.N - (self.write_pos[peer] - self.read_pos[peer]) - 1) < c:
                return False
        # ... otherwise all had enough slots
        return True

    def tokens_available(self, length, metadata):
        if not isinstance(metadata, basestring):
            raise Exception('Not a string: %s' % metadata)
        if metadata not in self.readers:
            raise Exception("No reader %s in %s" % (metadata, self.readers))
        return (self.write_pos[metadata] - self.tentative_read_pos[metadata]) >= length

    #
    # Reading is done tentatively until committed
    #
    def peek(self, metadata=None):
        if not isinstance(metadata, basestring):
            raise Exception('Not a string: %s' % metadata)
        if metadata not in self.readers:
            raise Exception("Unknown reader: '%s'" % metadata)
        if not self.tokens_available(1, metadata):
            raise QueueEmpty(reader=metadata)
        read_pos = self.tentative_read_pos[metadata]
        data = self.fifo[metadata][read_pos % self.N]
        self.tentative_read_pos[metadata] = read_pos + 1
        return data

    def commit(self, metadata=None):
        self.read_pos[metadata] = self.tentative_read_pos[metadata]

    def cancel(self, metadata=None):
        self.tentative_read_pos[metadata] = self.read_pos[metadata]

    #
    # Queue operations used by communication which utilize a sequence number
    #

    def com_write(self, data, sequence_nbr):
        peer = self.readers[self.reader_turn[self.turn_pos % self.N]]
        write_pos = self.write_pos[peer]
        if sequence_nbr == write_pos:
            self.write(data)
            return COMMIT_RESPONSE.handled
        elif sequence_nbr < write_pos:
            return COMMIT_RESPONSE.unhandled
        else:
            return COMMIT_RESPONSE.invalid

    def com_peek(self, metadata=None):
        pos = self.tentative_read_pos[metadata]
        return (pos, self.peek(metadata))

    def com_commit(self, reader, sequence_nbr):
        """ Will commit one token when the sequence_nbr matches
            return COMMIT_RESPONSE for action on token sequence_nbr.
            Only act on sequence nbrs at end of queue.
            reader: peer_id
            sequence_nbr: token sequence_nbr
        """
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
        if (sequence_nbr >= self.tentative_read_pos[reader] and
            sequence_nbr < self.reader_pos[reader]):
            return COMMIT_RESPONSE.invalid
        self.tentative_read_pos[reader] = sequence_nbr
        return COMMIT_RESPONSE.handled

    def com_is_committed(self, reader):
        return self.tentative_read_pos[reader] == self.read_pos[reader]

