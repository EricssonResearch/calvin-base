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

from calvin.runtime.south.plugins.async import server_connection
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
import json

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)

from calvin.utilities import calvinconfig
_conf = calvinconfig.get()


class WSServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        _log.debug("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        self.factory.register(self)

    def connectionLost(self, reason):
        _log.debug("WebSocket connection lost: {0}".format(reason))
        self.factory.unregister(self)
        WebSocketServerProtocol.connectionLost(self, reason)

    def onClose(self, wasClean, code, reason):
        _log.debug("WebSocket connection closed: {0}".format(reason))


class WSServerProtocolFactory(WebSocketServerFactory):
    def __init__(self, host, port, node_name=None):
        # WebSocketServerFactory will set self.isSecure, self.host, self.port, etc, from parsing url string
        control_interface_security = _conf.get("security", "control_interface_security")
        if control_interface_security == "tls":
            url = "wss://{}:{}".format(host, port)
        else:
            url = "ws://{}:{}".format(host, port)
        super(WSServerProtocolFactory, self).__init__(url=url)
        self.clients = []
        self._port = None
        self._node_name = node_name

    def register(self, client):
        if client not in self.clients:
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            self.clients.remove(client)

    def broadcast(self, msg):
        for c in self.clients:
            c.sendMessage(json.dumps(msg))

    def start(self, host, port):
        self.protocol = WSServerProtocol
        self._port = server_connection.reactor_listen(self._node_name, self, host, port)

    def stop(self):
        self._port.stopListening()
        for c in self.clients:
            c.sendClose()
