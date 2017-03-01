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

from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.port.queue.fanout_ordered_fifo import FanoutOrderedFIFO


_log = calvinlogger.get_logger(__name__)


class FanoutRoundRobinFIFO(FanoutOrderedFIFO):

    """
    A FIFO which route tokens based on a round-robin schedule to peers
    """

    def __init__(self, port_properties, peer_port_properties):
        super(FanoutRoundRobinFIFO, self).__init__(port_properties, peer_port_properties)
        self._type = "dispatch:round-robin"

    def _set_turn(self):
        self._update_turn = self._round_robin
        if self.reader_turn is None:
            # Populate with alternating values up to N
            self.reader_turn = [p for n in range(self.N) for p in range(self.nbr_peers)][:self.N]

    def _reset_turn(self):
        # Populate with alternating values up to N
        try:
            pos = self.reader_turn[self.turn_pos % self.N]
            self.reader_turn = [p for n in range(self.N) for p in range(self.nbr_peers)][pos:self.N+pos]
        except:
            # No readers
            self.reader_turn = []
        self.turn_pos = 0

    def _round_robin(self):
        reader = self.reader_turn[self.turn_pos % self.N]
        prev = self.reader_turn[(self.turn_pos - 1) % self.N]
        self.reader_turn[self.turn_pos % self.N] = (prev + 1) % self.nbr_peers
        self.turn_pos += 1
        return reader
