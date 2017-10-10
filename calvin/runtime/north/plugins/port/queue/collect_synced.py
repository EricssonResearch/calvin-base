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
from calvin.runtime.north.calvin_token import ExceptionToken
import copy

_log = calvinlogger.get_logger(__name__)

# TODO: Move tags to metadata

class CollectSynced(CollectBase):

    """
    Collect tokens from multiple peers, actions see
    them all as one token {<tag1>: <token1>, ... <tagN>: <tokenN>}.
    Use property tag on a connected outport otherwise tag defaults to port id.
    
    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectSynced, self).__init__(port_properties, peer_port_properties)
        self._type = "collect:all-tagged"

    def tokens_available(self, length, metadata):
        if length >= self.N:
            return False
        # All FIFOs need to have length tokens
        for metadata in self.writers:
            if self.write_pos[metadata] - self.tentative_read_pos[metadata] < length:
                return False
        return True
        
    def peek(self, metadata):
        if not self.tokens_available(1, metadata):
            raise QueueEmpty(reader=metadata)
        # value = {}
        values, metas = [], []
        # Collect all tokens 
        for writer in self.writers:
            read_pos = self.tentative_read_pos[writer]
            data = self.fifo[writer][read_pos % self.N]
            if isinstance(data, ExceptionToken):
                # We found an exception token, will return it alone
                # First cancel previous peeks
                for w in self.writers:
                    if w is writer:
                        break
                    self.tentative_read_pos[w] -= 1
                # # return exception token alone
                self.tentative_read_pos[writer] = read_pos + 1
                tok_class = data.__class__
                meta = data.metadata
                meta['port_tag'] = self.tags[writer]
                return tok_class(data.value, **meta)

            self.tentative_read_pos[writer] = read_pos + 1
            values.append(data.value)
            meta = data.metadata
            meta['port_tag'] = self.tags[writer] # FIXME: Get set port tag in src port 
            metas.append(meta)
        
        # Convert list of metadata dicts to dict of metadata lists
        meta = {'port_tag':[], 'origin':[], 'timestamp':[]}
        for m in metas:
            meta['port_tag'].append(m['port_tag'])
            meta['origin'].append(m.get('origin', None))
            meta['timestamp'].append(m.get('timestamp', None))

        return Token(values, **meta)

        
