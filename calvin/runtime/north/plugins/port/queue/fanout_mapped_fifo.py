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


class FanoutMappedFIFO(FanoutBase):

    """
    A FIFO which route tokens based on a mapping to peers
    """

    def __init__(self, port_properties, peer_port_properties):
        super(FanoutMappedFIFO, self).__init__(port_properties, peer_port_properties)
        self._type = "dispatch:mapped"

    def _state(self):
        state = super(FanoutMappedFIFO, self)._state()
        state['mapping'] = self.mapping
        return state

    def _set_state(self, state):
        super(FanoutMappedFIFO, self)._set_state(state)
        self.mapping = state['mapping']

    def _set_port_mapping(self, mapping):
        if not set(mapping.values()) == set(self.readers):
            print mapping, self.readers
            raise Exception("Illegal port mapping dictionary")
        self.mapping = mapping

    def _unwrap_data(self, data):
        # data is a Token whose value is wrapped in a {selector:value} dict
        mapped_value = data.value
        select, value = mapped_value.popitem()
        data.value = value
        peer = self.mapping[select]
        return data, peer

    def write(self, data, metadata):
        # print data, metadata
        # metadata is port_id of containing port
        data, peer = self._unwrap_data(data)
        if not self.slots_available(1, peer):
            # if not slots_available:
            raise QueueFull()
        # Write token in peer's FIFO
        write_pos = self.write_pos[peer]
        #_log.debug("WRITE2 %s %s %d\n%s" % (metadata, peer, write_pos, str(map(str, self.fifo[peer]))))
        self.fifo[peer][write_pos % self.N] = data
        self.write_pos[peer] = write_pos + 1
        return True

    def slots_available(self, length, metadata):
        # print "slots_available", length, metadata
        # Sometimes metadata = id of the outport owning this queue (called from @condition?)
        # Darn. That means that we can only check for the case where EVERY sub-queue has at least 'length' slots free...
        # Oh well, such is life.
        if metadata in self.readers:
            return self.write_pos[metadata] - self.read_pos[metadata] < self.N - length
        return all(self.write_pos[r] - self.read_pos[r] < self.N - length for r in self.readers)

