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

from calvin.runtime.south.plugins.async import server_connection


class Server(object):
    def __init__(self, node, mode, delimiter, max_length, actor_id=None):
        self.connection_factory = server_connection.ServerProtocolFactory(node.sched.trigger_loop, mode, delimiter, max_length, actor_id)

    def start(self, host, port):
        self.connection_factory.start(host, port)

    def stop(self):
        self.connection_factory.stop()

    def accept(self):
        return self.connection_factory.accept()

    def connection_pending(self):
        if self.connection_factory.pending_connections:
            return True
        return False

    def send(self, connection, data):
        connection.send(data)

    def receive(self, connection):
        return connection.data_get()


class ServerHandler(object):
    def __init__(self, node, actor):
        super(ServerHandler, self).__init__()
        self.node   = node
        self.server = None
        self._actor = actor

    def start(self, host, port, mode, delimiter, max_length):
        self.server = Server(self.node, mode, delimiter, max_length, actor_id=self._actor.id)
        self.server.start(host, port)
        return self.server

    def stop(self):
        self.server.stop()


def register(node, actor, io):
    """
        Called when the system object is first created.
    """
    io.tcp_server = ServerHandler(node, actor)
