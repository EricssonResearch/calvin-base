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
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.port.queue.fanout_ordered_fifo import FanoutOrderedFIFO


_log = calvinlogger.get_logger(__name__)


class FanoutRandomFIFO(FanoutOrderedFIFO):

    """
    A FIFO which route tokens randomly to peers

    """

    def __init__(self, port_properties, peer_port_properties):
        super(FanoutRandomFIFO, self).__init__(port_properties, peer_port_properties)
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