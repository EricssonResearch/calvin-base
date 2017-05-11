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
from calvin.utilities.calvinlogger import get_logger

from calvin.runtime.south.plugins.io.websocket import ws_server_connection
#from calvin.utilities import calvinconfig
#
_log = get_logger(__name__)
#
#try:
#    from calvin.runtime.south.plugins.io.websocket import ws_server_connection
#except ImportError as e:
#    _conf = calvinconfig.get()
#    if _conf.get('GLOBAL', 'websocket_plugin'):
#        _log.error("Loading plugin for websocket failed: %s" % e)
#


class WSServer(object):
    """ Only for broadcasting as of yet """
    def __init__(self, host, port, node_name, actor_id):
        super(WSServer, self).__init__()
        self.connection_factory = ws_server_connection.WSServerProtocolFactory(host, port, node_name)

    def start(self, host, port):
        self.connection_factory.start(host, port)

    def stop(self):
        self.connection_factory.stop()

    def clients_connected(self):
        return self.connection_factory.clients

    def broadcast(self, msg):
        self.connection_factory.broadcast(msg)


class WSServerHandler(object):
    def __init__(self, node, actor):
        super(WSServerHandler, self).__init__()
        self.node   = node
        self.server = None
        self._actor = actor

    def start(self, host, port):
        self.server = WSServer(host, port, self.node.node_name, actor_id=self._actor.id)
        self.server.start(host, port)
        return self.server

    def stop(self):
        self.server.stop()


def register(node, actor):
    """
        Called when the system object is first created.
    """
    return WSServerHandler(node, actor)
