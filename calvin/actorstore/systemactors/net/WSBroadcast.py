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

from calvin.actor.actor import Actor, manage, condition, stateguard

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


class WSBroadcast(Actor):
    """
    Broadcast any received token data to all connected clients via websocket.

    Inputs:
      token : Data received on this port will be sent to all connected clients.
    """

    @manage(['host', 'port'])
    def init(self, host, port):
        self.host = host
        self.port = port

        self.setup()

    def setup(self):
        self.server = self.use("calvinsys.network.websockethandler", shorthand="server")

    def will_migrate(self):
        self.server.stop()

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self.host and self.port and self.server is None)
    @condition()
    def start(self):
        try:
            self.server = self['server'].start(self.host, self.port)
        except Exception as e:
            _log.exception(e)
            self.server = None

    @stateguard(lambda self: self.server and self.server.clients_connected())
    @condition(['token'])
    def broadcast(self, token):
        self.server.broadcast(token)

    # add receive
    action_priority = (broadcast, start)
    requires = ['calvinsys.network.websockethandler']
