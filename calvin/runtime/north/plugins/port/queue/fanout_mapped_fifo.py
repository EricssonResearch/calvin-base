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

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty, COMMIT_RESPONSE
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


class FanoutMappedFIFO(object):

    """
    A FIFO which route tokens based on a schedule to peers
    Parameters:
        port_properties: dictionary must contain key 'routing' with
                         value 'round-robin' or 'random'
    """

    def __init__(self, port_properties, peer_port_properties):
        super(FanoutMappedFIFO, self).__init__()
        # Set default queue length to 4 if not specified
        length = port_properties.get('queue_length', 4)
        # Compensate length for FIFO having an unused slot
        length += 1
        # Each peer have it's own FIFO
        self.fifo = {}
        self.nbr_peers = port_properties.get('nbr_peers', 1)
        self.N = length
        self.readers = []
        # NOTE: For simplicity, modulo operation is only used in fifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = {}
        self.read_pos = {}
        self.tentative_read_pos = {}
        self.mapping = {}
        if isinstance(port_properties['routing'], (tuple, list)):
            routing = port_properties['routing'][0]
        else:
            routing = port_properties['routing']
        self._type = "scheduled_fifo:" + routing

    def __str__(self):
        fifo = "\n".join([str(k) + ": " + ", ".join(map(lambda x: str(x), self.fifo[k])) for k in self.fifo.keys()])
        return "Queue: %s\nTokens: %s\nw:%s, r:%s, tr:%s" % (self._type, fifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self, remap=None):
        if remap is None:
            state = {
                'queuetype': self._type,
                'fifo': {p: [t.encode() for t in tokens] for p, tokens in self.fifo.items()},
                'N': self.N,
                'readers': self.readers,
                'write_pos': self.write_pos,
                'read_pos': self.read_pos,
                'tentative_read_pos': self.tentative_read_pos,
                'mapping': self.mapping
            }
        else:
            # Remapping of port ids implies reset of tokens
            state = {
                'queuetype': self._type,
                'fifo': {remap[p] if p in remap else p: [Token(0).encode() for t in tokens] for p, tokens in self.fifo.items()},
                'N': self.N,
                'readers': sorted([remap[pid] if pid in remap else pid for pid in self.readers]),
                'write_pos': {remap[pid] if pid in remap else pid: 0 for pid in self.write_pos.keys()},
                'read_pos': {remap[pid] if pid in remap else pid: 0 for pid in self.read_pos.keys()},
                'tentative_read_pos': {remap[pid] if pid in remap else pid: 0 for pid in self.tentative_read_pos.keys()},
                'mapping': {k : remap.get(pid, pid) for k, pid in self.mapping.iteritems()}
            }
        return state

    def _set_state(self, state):
        self._type = state.get('queuetype')
        self.fifo = {p: [Token.decode(t) for t in tokens] for p, tokens in state['fifo'].items()}
        self.N = state['N']
        self.readers = state['readers']
        self.write_pos = state['write_pos']
        self.read_pos = state['read_pos']
        self.tentative_read_pos = state['tentative_read_pos']
        if len(self.readers) > self.nbr_peers:
            # If the peer has been replicated just set it to nbr connected
            self.nbr_peers = len(self.readers)

    def _set_port_mapping(self, mapping):
        if not set(mapping.values()) == set(self.readers):
            print mapping, self.readers
            raise Exception("Illegal port mapping dictionary")
        self.mapping = mapping

    @property
    def queue_type(self):
        return self._type

    def set_config(self, config):
        """
        Set additional config information on the port.
        The 'config' parameter is a dictionary with settings.
        """
        if 'port-mapping' in config:
            self._set_port_mapping(config['port-mapping'])

    def add_writer(self, writer, properties):
        pass

    def remove_writer(self, writer):
        pass

    def add_reader(self, reader, properties):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        # print "add_reader():"
        # print "    reader:", reader
        # print "    properties:", properties

        if reader not in self.readers:
            self.read_pos[reader] = 0
            self.write_pos[reader] = 0
            self.tentative_read_pos[reader] = 0
            self.fifo.setdefault(reader, [Token(0)] * self.N)
            self.readers.append(reader)
            # self.readers.sort()
        if len(self.readers) > self.nbr_peers:
            _log.debug("ADD_READER %s" % reader)
            self.nbr_peers = len(self.readers)

    def remove_reader(self, reader):
        if reader not in self.readers:
            return
        del self.read_pos[reader]
        del self.tentative_read_pos[reader]
        del self.write_pos[reader]
        del self.fifo[reader]
        self.readers.remove(reader)
        self.nbr_peers -= 1

    def is_exhausting(self, peer_id=None):
        return False

    def exhaust(self, peer_id, terminate):
        _log.debug("exhaust %s %s %s" % (self._type, peer_id, DISCONNECT.reverse_mapping[terminate]))
        if peer_id not in self.readers:
            # FIXME handle writer
            return []
        if terminate == DISCONNECT.EXHAUST_PEER_SEND or terminate == DISCONNECT.EXHAUST_OUTPORT:
            # Retrive remaining tokens to be returned
            tokens = []
            for read_pos in range(self.read_pos[peer_id], self.write_pos[peer_id]):
                tokens.append([read_pos, self.fifo[peer_id][read_pos % self.N]])
            # Remove the queue to peer, so no more writing
            self.remove_reader(peer_id)
            return tokens
        else:
            self.remove_reader(peer_id)
        return []

    def set_exhausted_tokens(self, tokens):
        _log.debug("exhausted_tokens %s %s" % (self._type, tokens))
        if tokens and tokens.values()[0]:
            _log.error("Got exhaust tokens on scheduler_fifo port %s" % str(tokens))
        return self.nbr_peers

    def get_peers(self):
        return self.readers

    def _unwrap_data(self, data):
        # data is a Token whose value is wrapped in a {selector:value} dict
        mapped_value = data.value
        select, value = mapped_value.popitem()
        data.value = value
        peer = self.mapping[select]
        return data, peer

    def write(self, data, metadata):
        # print data, metadata
        # metadata is port_id of containing port
        data, peer = self._unwrap_data(data)
        if not self.slots_available(1, peer):
            # if not slots_available:
            raise QueueFull()
        # Write token in peer's FIFO
        write_pos = self.write_pos[peer]
        #_log.debug("WRITE2 %s %s %d\n%s" % (metadata, peer, write_pos, str(map(str, self.fifo[peer]))))
        self.fifo[peer][write_pos % self.N] = data
        self.write_pos[peer] = write_pos + 1
        return True

    def slots_available(self, length, metadata):
        # print "slots_available", length, metadata
        # Sometimes metadata = id of the outport owning this queue (called from @condition?)
        # Darn. That means that we can only check for the case where EVERY sub-queue has at least 'length' slots free...
        # Oh well, such is life.
        if metadata in self.readers:
            return self.write_pos[metadata] - self.read_pos[metadata] < self.N - length
        return all(self.write_pos[r] - self.read_pos[r] < self.N - length for r in self.readers)

    def tokens_available(self, length, metadata):
        if metadata not in self.readers:
            raise Exception("No reader %s in %s" % (metadata, self.readers))
        return (self.write_pos[metadata] - self.tentative_read_pos[metadata]) >= length

    #
    # Reading is done tentatively until committed
    #
    def peek(self, metadata):
        # print "peek", metadata
        if not self.tokens_available(1, metadata):
            raise QueueEmpty(reader=metadata)
        read_pos = self.tentative_read_pos[metadata]
        data = self.fifo[metadata][read_pos % self.N]
        self.tentative_read_pos[metadata] = read_pos + 1
        return data

    def commit(self, metadata):
        self.read_pos[metadata] = self.tentative_read_pos[metadata]
        return False

    def cancel(self, metadata):
        self.tentative_read_pos[metadata] = self.read_pos[metadata]

    #
    # Queue operations used by communication which utilize a sequence number
    #

    def com_write(self, data, metadata, sequence_nbr):
        # peer = self.readers[self.reader_turn[self.turn_pos % self.N]]
        data, peer = self._unwrap_data(data)
        write_pos = self.write_pos[peer]
        # FIXME: @Harald: Is this really correct?
        if sequence_nbr == write_pos:
            self.write(data, metadata)
            return COMMIT_RESPONSE.handled
        elif sequence_nbr < write_pos:
            return COMMIT_RESPONSE.unhandled
        else:
            return COMMIT_RESPONSE.invalid

    def com_peek(self, metadata):
        pos = self.tentative_read_pos[metadata]
        #_log.debug("COM_PEEK %s read_pos: %d" % (metadata, pos))
        r = (pos, self.peek(metadata))
        #_log.debug("COM_PEEK2 %s read_pos: %d" % (metadata, pos))
        return r

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

