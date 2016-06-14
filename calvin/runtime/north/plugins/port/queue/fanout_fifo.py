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
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

class FanoutFIFO(object):

    """
    A FIFO with fanout support
    Parameters:
        length is the number of entries in the FIFO
        readers is a set of peer port ids reading from the FIFO
    """

    def __init__(self, port_properties):
        super(FanoutFIFO, self).__init__()
        # Set default queue length to 4 if not specified
        try:
            length = port_properties.get('queue_length', 4)
        except:
            length = 4
        # Compensate length for FIFO having an unused slot
        length += 1
        self.fifo = [Token(0)] * length
        self.N = length
        self.readers = set()
        # NOTE: For simplicity, modulo operation is only used in fifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = 0
        self.read_pos = {}
        self.tentative_read_pos = {}
        self._type = "fanout_fifo"

    def __str__(self):
        return "Tokens: %s, w:%i, r:%s, tr:%s" % (self.fifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self):
        state = {
            'queuetype': self._type,
            'fifo': [t.encode() for t in self.fifo],
            'N': self.N,
            'readers': list(self.readers),
            'write_pos': self.write_pos,
            'read_pos': self.read_pos,
            'tentative_read_pos': self.tentative_read_pos
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

    @property
    def queue_type(self):
        return self._type

    def add_reader(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        if reader not in self.readers:
            self.read_pos[reader] = 0
            self.tentative_read_pos[reader] = 0
            self.readers.add(reader)

    def remove_reader(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        del self.read_pos[reader]
        del self.tentative_read_pos[reader]
        self.readers.discard(reader)

    def write(self, data):
        if not self.slots_available(1):
            raise QueueFull()
        write_pos = self.write_pos
        self.fifo[write_pos % self.N] = data
        self.write_pos = write_pos + 1
        return True

    def slots_available(self, length):
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

    def commit_one_read(self, reader, commit=True):
        if self.read_pos[reader] < self.tentative_read_pos[reader]:
            if commit:
                self.read_pos[reader] += 1
            else:
                self.tentative_read_pos[reader] -= 1
