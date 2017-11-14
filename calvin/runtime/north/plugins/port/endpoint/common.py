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

from calvin.runtime.north.plugins.port import DISCONNECT

class Endpoint(object):

    """docstring for Endpoint"""

    _void_endpoint = None

    def __init__(self, port, former_peer_id=None):
        super(Endpoint, self).__init__()
        self.port = port
        self.former_peer_id = former_peer_id
        self.remaining_tokens = {}

    def __str__(self):
        return "%s(port_id=%s)" % (self.__class__.__name__, self.port.id)

    @classmethod
    def void(cls):
        if Endpoint._void_endpoint is None:
           Endpoint._void_endpoint = Endpoint(None)
        return Endpoint._void_endpoint

    def is_connected(self):
        return False

    def use_monitor(self):
        return False

    def register(self, registry):
        if self.use_monitor():
            registry.register_endpoint(self)

    def unregister(self, registry):
        if self.use_monitor():
            registry.unregister_endpoint(self)

    def communicate(self):
        """
        Called by the runtime when it is possible to transfer data to counterpart.
        """
        raise Exception("Can't communicate on endpoint in port %s.%s with id: %s" % (
            self.port.owner.name, self.port.name, self.port.id))

    def destroy(self):
        pass

    def get_peer(self):
        return (None, self.former_peer_id)

    def attached(self):
        pass

    def detached(self, terminate=DISCONNECT.TEMPORARY):
        pass
