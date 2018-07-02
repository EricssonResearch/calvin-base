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

from calvin.runtime.north.plugins.port.queue.common import QueueFull
from calvin.runtime.north.plugins.port.queue.fanout_base import FanoutBase

from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


class FanoutOrderedFIFO(FanoutBase):

    """
    A FIFO which route tokens based on an ordering to peers

    """

    def __init__(self, port_properties, peer_port_properties):
        super(FanoutOrderedFIFO, self).__init__(port_properties, peer_port_properties)
        self.reader_turn = None
        self.turn_pos = 0
        self._set_turn()
        self._is_ordered = False
        self._type = "dispatch:ordered"

    def _set_turn(self):
        # Get routing schedule based on info after ':' in type
        # Set the correct method
        self._update_turn = self._ordered
        if self.reader_turn is None:
            # Populate with alternating values up to N
            self.reader_turn = [p for n in range(self.N) for p in range(self.nbr_peers)][:self.N]
        # print "_set_turn(): "
        # print "    self._update_turn:", self._update_turn
        # print "    self.reader_turn:", self.reader_turn

    def _reset_turn(self):
        # Populate with alternating values up to N
        pos = self.reader_turn[self.turn_pos % self.N]
        self.reader_turn = [p for n in range(self.N) for p in range(self.nbr_peers)][pos:self.N+pos]
        self.turn_pos = 0

    def _ordered(self):
        reader = self.reader_turn[self.turn_pos % self.N]
        prev = self.reader_turn[(self.turn_pos - 1) % self.N]
        self.reader_turn[self.turn_pos % self.N] = (prev + 1) % self.nbr_peers
        self.turn_pos += 1
        # print "_ordered():"
        # print "    reader:", reader
        # print "    self.reader_turn:", self.reader_turn
        return reader

    def _state(self):
        state = super(FanoutOrderedFIFO, self)._state()
        state['reader_turn'] = self.reader_turn
        state['turn_pos'] = self.turn_pos
        return state

    def _set_state(self, state):
        super(FanoutOrderedFIFO, self)._set_state(state)
        self.reader_turn = state['reader_turn']
        self.turn_pos = state['turn_pos']
        self._set_turn()

    def _set_port_order(self, order):
        if not set(order) == set(self.readers):
            # print order, self.readers
            raise Exception("Illegal port order list")
        self.readers = order
        self._is_ordered = True

    def add_reader(self, reader, properties):
        super(FanoutOrderedFIFO, self).add_reader(reader, properties)
        if not self._is_ordered:
            # Once a port ordering is set we no longer re-sort the list
            self.readers.sort()

    def remove_reader(self, reader):
        removed = super(FanoutOrderedFIFO, self).remove_reader(reader)
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
