# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

# encoding: utf-8

from calvin.actor.actor import Actor, manage, condition, calvinsys, stateguard

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


class WSBroadcast(Actor):
    """
    Broadcast any received token data to all connected clients via websocket.

    Inputs:
      token : Data received on this port will be sent to all connected clients.
    """

    @manage(['host', 'port', 'server'])
    def init(self, host, port):
        self.host = host
        self.port = port
        self.server = calvinsys.open(self, "web.websocket.broadcast", host=host, port=port)

    @stateguard(lambda self: self.server and calvinsys.can_write(self.server))
    @condition(['token'])
    def broadcast(self, token):
        calvinsys.write(self.server, token)

    action_priority = (broadcast,)
    requires = ['web.websocket.broadcast']

    test_kwargs = {'host': '123.45.67.8', 'port': 9999}
    test_calvinsys = {'web.websocket.broadcast': {'write': ["test"]}}
    test_set = [
        {
            'inports': {'token': ['test']}
        }
    ]
