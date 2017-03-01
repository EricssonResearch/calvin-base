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
from calvin.runtime.north.plugins.port.queue.common import QueueEmpty
from calvin.runtime.north.plugins.port.queue.collect_base import CollectBase
from calvin.utilities import calvinlogger
from calvin.runtime.north.calvin_token import ExceptionToken
import copy

_log = calvinlogger.get_logger(__name__)


class CollectAny(CollectBase):

    """
    Collect tokens from multiple peers, actions see
    them as one token {<tag1>: <token1>, ... <tagN>: <tokenN>}. The collected
    token is available when any of the peers have delivered tokens.
    Use property tag on a connected outport otherwise tag defaults to port id.
    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectAny, self).__init__(port_properties, peer_port_properties)
        self._type = "collect:any-tagged"

    def tokens_available(self, length, metadata):
        if length >= self.N:
            return False
        # Any FIFOs need to have length tokens
        for metadata in self.writers:
            if self.write_pos[metadata] - self.tentative_read_pos[metadata] >= length:
                return True
        return False

    def peek(self, metadata):
        value = {}
        for writer in self.writers:
            if self.write_pos[writer] == self.tentative_read_pos[writer]:
                continue
            read_pos = self.tentative_read_pos[writer]
            data = self.fifo[writer][read_pos % self.N]
            if isinstance(data, ExceptionToken):
                # We found an exception token, will return it alone
                # First cancel previous peeks
                for w in self.writers:
                    if w is writer:
                        break
                    self.tentative_read_pos[w] -= 1
                # return exception token alone
                data = copy.deepcopy(data)
                data.value = {self.tags[writer]: data.value}
                self.tentative_read_pos[writer] = read_pos + 1
                return data
            self.tentative_read_pos[writer] = read_pos + 1
            value[self.tags[writer]] = data.value
        if value:
            return Token(value)
        else:
            raise QueueEmpty(reader=metadata)
            

    def _set_port_mapping(self, mapping):
        if not set(mapping.values()) == set(self.writers):
            print mapping, self.readers
            raise Exception("Illegal port mapping dictionary")
        self.tags = { v: k for k,v in mapping.items() }


