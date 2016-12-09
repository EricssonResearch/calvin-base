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
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.port.queue.scheduled_fifo import ScheduledFIFO

_log = calvinlogger.get_logger(__name__)


class BalancedQueue(ScheduledFIFO):

    """
    A queue which route tokens trying to keep to peers equally busy
    Parameters:
        port_properties: dictionary must contain key 'routing' with
                         value 'balanced'
    """

    def __init__(self, port_properties, peer_port_properties):
        super(BalancedQueue, self).__init__(port_properties, peer_port_properties)

    def _set_turn(self):
        self._update_turn = lambda self: True

    def _reset_turn(self):
        pass

    def write(self, data, metadata):
        slots = []
        full = True
        for reader in self.readers:
            s = self.N - (self.write_pos[reader] - self.read_pos[reader]) - 1
            slots.append((s, reader))
            if s > 0:
                full = False
        if full:
            raise QueueFull()
        # Write token in peer with most slots FIFO
        peer = max(slots)[1]
        write_pos = self.write_pos[peer]
        self.fifo[peer][write_pos % self.N] = data
        self.write_pos[peer] = write_pos + 1
        return True

    def slots_available(self, length, metadata):
        if length >= self.N:
            return False
        # Sum slots from all reader FIFOs when more than length OK
        slots = 0
        for reader in self.readers:
            slots += self.N - (self.write_pos[reader] - self.read_pos[reader]) - 1
            if slots >= length:
                return True
        return False