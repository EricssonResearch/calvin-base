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


class CollectBase(object):

    """
    A queue with fanin support, does not handle token order between connections
    only within a connection.
    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectBase, self).__init__()
        # Set default queue length to 4 if not specified
        length = port_properties.get('queue_length', 4)
        # Compensate length for FIFO having an unused slot
        length += 1
        # Each peer have it's own FIFO
        self.fifo = {}
        self.nbr_peers = port_properties.get('nbr_peers', 1)
        self.N = length
        # Peers ordered by id
        self.writers = []
        # NOTE: For simplicity, modulo operation is only used in fifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = {}
        self.read_pos = {}
        self.tentative_read_pos = {}
        self.tags = {}

    def __str__(self):
        fifo = "\n".join([str(k) + ": " + ", ".join(map(lambda x: str(x), self.fifo[k])) for k in self.fifo.keys()])
        return "Tokens: %s\nw:%s, r:%s, tr:%s" % (fifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self, remap=None):
        if remap is None:
            state = {
                'queuetype': self._type,
                'fifo': {p: [t.encode() for t in tokens] for p, tokens in self.fifo.items()},
                'N': self.N,
                'writers': self.writers,
                'write_pos': self.write_pos,
                'read_pos': self.read_pos,
                'tentative_read_pos': self.tentative_read_pos,
                'tags': self.tags
            }
        else:
            state = {
                'queuetype': self._type,
                'fifo': {p: [Token(0).encode() for t in tokens] for p, tokens in self.fifo.items()},
                'N': self.N,
                'writers': sorted([pid for pid in self.writers]),
                'write_pos': {pid: 0 for pid in self.write_pos.keys()},
                'read_pos': {pid: 0 for pid in self.read_pos.keys()},
                'tentative_read_pos': {pid: 0 for pid in self.tentative_read_pos.keys()},
                # TODO Need unique tags, how should these be created
                'tags': {pid: tag for pid, tag in self.tags.items()}
            }
        return state

    def _set_state(self, state):
        self._type = state.get('queuetype')
        self.fifo = {p: [Token.decode(t) for t in tokens] for p, tokens in state['fifo'].items()}
        self.N = state['N']
        self.writers = state['writers']
        self.write_pos = state['write_pos']
        self.read_pos = state['read_pos']
        self.tentative_read_pos = state['tentative_read_pos']
        self.tags = state.get("tags", {})

    @property
    def queue_type(self):
        return self._type

    def add_writer(self, writer, properties):
        if not isinstance(writer, basestring):
            raise Exception('Not a string: %s' % writer)
        if writer not in self.writers:
            self.read_pos[writer] = 0
            self.write_pos[writer] = 0
            self.tentative_read_pos[writer] = 0
            self.fifo.setdefault(writer, [Token(0)] * self.N)
            self.writers.append(writer)
            self.writers.sort()
        if len(self.writers) > self.nbr_peers:
            _log.debug("ADD_WRITER %s" % writer)
            self.nbr_peers = len(self.writers)

        self.tags[writer] = properties.get("tag", writer)

    def remove_writer(self, writer):
        if not isinstance(writer, basestring):
            raise Exception('Not a string: %s' % writer)
        del self.read_pos[writer]
        del self.tentative_read_pos[writer]
        del self.write_pos[writer]
        self.writers.remove(writer)

    def add_reader(self, reader, properties):
        pass

    def remove_reader(self, reader):
        pass

    def get_peers(self):
        return self.writers

    def write(self, data, metadata):
        if not self.slots_available(1, metadata):
            raise QueueFull()
        # Write token in peer's FIFO
        write_pos = self.write_pos[metadata]
        self.fifo[metadata][write_pos % self.N] = data
        self.write_pos[metadata] = write_pos + 1
        return True

    def slots_available(self, length, metadata):
        if not isinstance(metadata, basestring):
            raise Exception('Not a string: %s' % metadata)
        if metadata not in self.writers:
            raise Exception("No writer %s in %s" % (metadata, self.writers))
        return length < self.N and (self.write_pos[metadata] - self.read_pos[metadata]) < (self.N - length)

    def tokens_available(self, length, metadata):
        raise NotImplementedError("Sub-class must override")

    #
    # Reading is done tentatively until committed
    # The commit and cancel are only used in action firings not communication.
    # It is always all peeked tokens that are commited or canceled.
    #
    def peek(self, metadata=None):
        raise NotImplementedError("Sub-class must override")

    def commit(self, metadata=None):
        for writer in self.writers:
            self.read_pos[writer] = self.tentative_read_pos[writer]

    def cancel(self, metadata=None):
        for writer in self.writers:
            self.tentative_read_pos[writer] = self.read_pos[writer]

    #
    # Queue operations used by communication which utilize a sequence number
    #

    def com_write(self, data, metadata, sequence_nbr):
        write_pos = self.write_pos[metadata]
        if sequence_nbr == write_pos:
            self.write(data, metadata)
            return COMMIT_RESPONSE.handled
        elif sequence_nbr < write_pos:
            return COMMIT_RESPONSE.unhandled
        else:
            return COMMIT_RESPONSE.invalid

    def com_peek(self, metadata=None):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

    def com_commit(self, reader, sequence_nbr):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

    def com_cancel(self, reader, sequence_nbr):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

    def com_is_committed(self, reader):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

