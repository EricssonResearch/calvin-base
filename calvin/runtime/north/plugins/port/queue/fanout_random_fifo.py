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
from calvin.runtime.north.plugins.port.queue.common import QueueFull
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.port.queue.fanout_base import FanoutBase


_log = calvinlogger.get_logger(__name__)


class FanoutRandomFIFO(FanoutBase):

    """
    A FIFO which route tokens randomly to peers

    """
    def __init__(self, port_properties, peer_port_properties):
        super(FanoutRandomFIFO, self).__init__(port_properties, peer_port_properties)
        self.reader_turn = None
        self.turn_pos = 0
        self._set_turn()
        self._type = "dispatch:random"
        
    def _set_turn(self):
        self._update_turn = self._random
        if self.reader_turn is None:
            # Populate with random values up to N
            self.reader_turn = [random.randrange(self.nbr_peers) for n in range(self.N)]

    def _reset_turn(self):
        # Populate with random values up to N
        try:
            self.reader_turn = [random.randrange(self.nbr_peers) for n in range(self.N)]
        except:
            # No readers
            self.reader_turn = []
        self.turn_pos = 0

    def _random(self):
        reader = self.reader_turn[self.turn_pos % self.N]
        self.reader_turn[self.turn_pos % self.N] = random.randrange(self.nbr_peers)
        self.turn_pos += 1
        return reader
        
    def _state(self, remap=None):
        state = super(FanoutRandomFIFO, self)._state(remap)
        if remap is None:
            state['reader_turn'] = self.reader_turn
            state['turn_pos'] = self.turn_pos
        else :
            state['reader_turn'] = None
            state['turn_pos'] = 0
        return state

    def _set_state(self, state):
        super(FanoutRandomFIFO, self)._set_state(state)
        self.reader_turn = state['reader_turn']
        self.turn_pos = state['turn_pos']
        self._set_turn()

    def add_reader(self, reader, properties):
        super(FanoutRandomFIFO, self).add_reader(reader, properties)
        self.readers.sort()
    
    def remove_reader(self, reader):
        removed = super(FanoutRandomFIFO, self).remove_reader(reader)
        if removed:
            self._reset_turn()
        return removed
            
    def write(self, data, metadata):
        #_log.debug("WRITE1 %s" % metadata)
        if not self.slots_available(1, metadata):
            raise QueueFull()
        # Write token in peer's FIFO
        peer = self.readers[self._update_turn()]
        write_pos = self.write_pos[peer]
        #_log.debug("WRITE2 %s %s %d\n%s" % (metadata, peer, write_pos, str(map(str, self.fifo[peer]))))
        self.fifo[peer][write_pos % self.N] = data
        self.write_pos[peer] = write_pos + 1
        return True

    def slots_available(self, length, metadata):
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
        