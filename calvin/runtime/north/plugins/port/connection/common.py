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

from calvin.utilities.utils import enum
PURPOSE = enum('INIT', 'CONNECT', 'DISCONNECT')

class BaseConnection(object):
    """BaseConnection"""

    def __init__(self, node, purpose, port, peer_port_meta, callback, factory, *args, **kwargs):
        super(BaseConnection, self).__init__()
        self.node = node
        self.purpose = purpose
        self.port = port
        self.peer_port_meta = peer_port_meta
        self.callback = callback
        self.factory = factory
        self._parallel_connections = []

    def async_reply(self, status):
        if not self.callback:
            return
        self.callback(
            status=status,
            actor_id=self.port.owner.id,
            port_name=self.port.name,
            port_id=self.port.id,
            peer_node_id=self.peer_port_meta.node_id,
            peer_actor_id=self.peer_port_meta.actor_id,
            peer_port_name=self.peer_port_meta.port_name,
            peer_port_id=self.peer_port_meta.port_id
        )

    def parallel_connections(self, connections):
        self._parallel_connections = connections

    def parallel_set(self, key, value):
        for c in self._parallel_connections:
            setattr(c, key, value)

    def init(self):
        return None

    def __str__(self):
        return "%s(port_id=%s, peer_port_id=%s)" % (self.__class__.__name__, self.port.id, self.peer_port_meta.port_id)


