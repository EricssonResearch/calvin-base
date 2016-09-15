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
from calvin.runtime.north.plugins.port.queue.collect_base import CollectBase
from calvin.utilities import calvinlogger
import copy

_log = calvinlogger.get_logger(__name__)


class CollectUnordered(CollectBase):

    """
    A queue with fanin support, does not handle token order between connections
    only within a connection.
    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectUnordered, self).__init__(port_properties, peer_port_properties)
        self.turn_pos = 0
        if isinstance(port_properties['routing'], (tuple, list)):
            routing = port_properties['routing'][0].split("-",1)[1]
        else:
            routing = port_properties['routing'].split("-",1)[1]
        self._type = "collect:" + routing

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

    def peek(self, metadata=None):
        for i in xrange(self.turn_pos, self.turn_pos + len(self.writers)):
            writer = self.writers[i % len(self.writers)]
            if self.write_pos[writer] - self.tentative_read_pos[writer] >= 1:
                read_pos = self.tentative_read_pos[writer]
                data = self.fifo[writer][read_pos % self.N]
                self.tentative_read_pos[writer] = read_pos + 1
                self.turn_pos += 1
                if self._type == "collect:tagged":
                    # Modify token to tagged value
                    # Make copy so that repeated peeks are not repeatedly tagging
                    # Also copy to preserv Token class, potential exception token.
                    data = copy.deepcopy(data)
                    data.value = {self.tags[writer]: data.value}
                return data
        raise QueueEmpty(reader=metadata)
