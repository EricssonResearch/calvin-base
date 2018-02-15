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

from calvin.runtime.north.plugins.port.queue.common import QueueEmpty
from calvin.runtime.north.plugins.port.queue.collect_base import CollectBase
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


class CollectUnordered(CollectBase):
    """
   Collect tokens from multiple peers, actions see them individually in without order between peers.
    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectUnordered, self).__init__(port_properties, peer_port_properties)
        self.turn_pos = 0
        self._type = "collect:unordered"
        self.peek_turn_pos = -1

    def _state(self):
        state = super(CollectUnordered, self)._state()
        state['turn_pos'] = self.turn_pos
        return state

    def _set_state(self, state):
        super(CollectUnordered, self)._set_state(state)
        self.turn_pos = state["turn_pos"]

    def tokens_available(self, length, metadata):
        if length >= self.N:
            return False
        available = 0
        for metadata in self.writers:
            available += self.write_pos[metadata] - self.tentative_read_pos[metadata]
            if available >= length:
                return True
        return False

    def peek(self, metadata):
        for i in xrange(self.turn_pos, self.turn_pos + len(self.writers)):
            writer = self.writers[i % len(self.writers)]
            if self.write_pos[writer] - self.tentative_read_pos[writer] >= 1:
                read_pos = self.tentative_read_pos[writer]
                data = self.fifo[writer][read_pos % self.N]
                self.tentative_read_pos[writer] = read_pos + 1
                if self.peek_turn_pos == -1:
                    self.peek_turn_pos = self.turn_pos
                self.turn_pos = (i + 1)  % len(self.writers)
                return data
        raise QueueEmpty(reader=metadata)

    def commit(self, metadata):
        self.peek_turn_pos = -1
        return super(CollectUnordered, self).commit(metadata)

    def cancel(self, metadata):
        self.turn_pos = self.peek_turn_pos
        self.peek_turn_pos = -1
        super(CollectUnordered, self).cancel(metadata)