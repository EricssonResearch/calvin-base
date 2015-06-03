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

from calvin_token import Token


class FIFO(object):

    """
    A FIFO for Calvin
    Parameters:
        length is the number of entries in the FIFO
        readers is a set of actors reading from the FIFO
    """

    # FIXME: (MAJOR) Readers must be UUIDs instead of sockets or we can't
    # migrate

    def __init__(self, length):
        super(FIFO, self).__init__()
        self.fifo = [Token(0)] * length
        self.N = length
        self.readers = set()
        # NOTE: For simplicity, modulo operation is only used in fifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = 0
        self.read_pos = {}
        self.tentative_read_pos = {}

    def __len__(self):
        return self.write_pos - min(self.read_pos.values() or [0])

    def __str__(self):
        return "Tokens: %s, w:%i, r:%s, tr:%s" % (self.fifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self):
        state = {
            'fifo': [t.encode() for t in self.fifo],
            'N': self.N,
            'readers': list(self.readers),
            'write_pos': self.write_pos,
            'read_pos': self.read_pos,
            'tentative_read_pos': self.tentative_read_pos
        }
        return state

    def _set_state(self, state):
        self.fifo = [Token.decode(d) for d in state['fifo']]
        self.N = state['N']
        self.readers = set(state['readers'])
        self.write_pos = state['write_pos']
        self.read_pos = state['read_pos']
        self.tentative_read_pos = state['tentative_read_pos']

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

    def can_write(self):
        # See if there is space to write data
        last_readpos = min(self.read_pos.values() or [0])
        return not (self.write_pos + 1) % self.N == last_readpos % self.N

    def write(self, data):
        if not self.can_write():
            return False
        write_pos = self.write_pos
        self.fifo[write_pos % self.N] = data
        self.write_pos = write_pos + 1
        return True

    def available_slots(self):
        # See if there is space to write data
        last_readpos = min(self.read_pos.values() or [0])
        return self.N - ((self.write_pos - last_readpos) % self.N) - 1

    def available_tokens(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        if reader not in self.readers:
            raise Exception("No reader")
        return self.write_pos - self.tentative_read_pos[reader]

    #
    # Reading is now done tentatively until committed
    #
    def can_read(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        if reader not in self.readers:
            raise Exception("No reader")
        return not self.tentative_read_pos[reader] == self.write_pos

    def read(self, reader):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        if reader not in self.readers:
            raise Exception("Unknown reader: '%s'" % reader)
        if not self.can_read(reader):
            return None
        read_pos = self.tentative_read_pos[reader]
        data = self.fifo[read_pos % self.N]
        self.tentative_read_pos[reader] = read_pos + 1
        return data

    # Commit is always required after reads.
    def commit_reads(self, reader, commit=True):
        if commit:
            self.read_pos[reader] = self.tentative_read_pos[reader]
        else:
            self.tentative_read_pos[reader] = self.read_pos[reader]

    def rollback_reads(self, reader):
        self.commit_reads(reader, False)

    def commit_one_read(self, reader, commit=True):
        if self.read_pos[reader] < self.tentative_read_pos[reader]:
            if commit:
                self.read_pos[reader] += 1
            else:
                self.tentative_read_pos[reader] -= 1
