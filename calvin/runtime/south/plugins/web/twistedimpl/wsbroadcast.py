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


class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

    def onClose(self, wasClean, code, reason):
        _log.info("WebSocket connection closed: {0}".format(reason))


class BroadcastServerFactory(WebSocketServerFactory):

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []
        self.tickcount = 0

    def register(self, client):
        if client not in self.clients:
            _log.info("registered client {}".format(client.peer))
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            _log.info("unregistered client {}".format(client.peer))
            self.clients.remove(client)

    def broadcast(self, msg):
        for c in self.clients:
            c.sendMessage(json.dumps(msg))
            _log.debug("message sent to {}".format(c.peer))

    def sendClose(self):
        for c in self.clients:
            c.sendClose()


class MyBroadcastServer(object):

    def __init__(self, host, port, actor_id=None, node_name=None):
        # WebSocketServerFactory will set self.isSecure, self.host, self.port, etc, from parsing url string
        control_interface_security = _conf.get("security", "control_interface_security")
        if control_interface_security == "tls":
            url = "wss://{}:{}".format(host, port)
        else:
            url = "ws://{}:{}".format(host, port)
        self._actor_id = actor_id
        self._node_name = node_name

        self.factory = BroadcastServerFactory(url)
        self.factory.protocol = BroadcastServerProtocol
        self._port = server_connection.reactor_listen(self._node_name, self.factory, host, port)

    def broadcast(self, msg):
        self.factory.broadcast(msg)

    def stop(self):
        self._port.stopListening()
        self.factory.sendClose()
