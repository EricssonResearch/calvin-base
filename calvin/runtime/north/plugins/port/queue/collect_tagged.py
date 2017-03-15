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
from calvin.runtime.north.plugins.port.queue.collect_unordered import CollectUnordered
from calvin.utilities import calvinlogger
import copy

_log = calvinlogger.get_logger(__name__)


class CollectTagged(CollectUnordered):

    """
    Collect tokens from multiple peers, actions see
    them individually as {<tag>: token}. Use property tag on
    a connected outport otherwise tag defaults to port id.

    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectTagged, self).__init__(port_properties, peer_port_properties)
        self._type = "collect:tagged"

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
                # Modify token to tagged value
                # Make copy so that repeated peeks are not repeatedly tagging
                # Also copy to preserv Token class, potential exception token.
                data = copy.deepcopy(data)
                data.value = {self.tags[writer]: data.value}
                return data
        raise QueueEmpty(reader=metadata)

    def _set_port_mapping(self, mapping):
        if not set(mapping.values()) == set(self.writers):
            print mapping, self.writers
            raise Exception("Illegal port mapping dictionary")
        self.tags = { v: k for k,v in mapping.items() }