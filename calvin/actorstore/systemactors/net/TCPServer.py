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

# encoding: utf-8

from calvin.actor.actor import Actor, manage, condition, stateguard
# from calvin.runtime.north.calvin_token import EOSToken

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


class TCPServer(Actor):
    """
    Etablish a TCP connection and forward all tokens except EOST on this connection.
    Any recevied data on the TCP connection is forwarded according to either Line mode or Raw mode.

    Inputs:
      host   : The host name as a string
      port   : The port number
      handle : A handle to the connection for which the data is meant.
      token  : Each received token will be sent to the client matching the handle.
    Output:
      handle : A handle to the connection from which the data was received.
      token  : Data received on the TCP connection will be sent as tokens.
    """

    @manage(['host', 'port', 'mode', 'delimiter', 'max_length'])
    def init(self, mode='line', delimiter='\r\n', max_length=8192):
        self.host                = None
        self.port                = None
        self.server              = None
        self.mode                = mode
        self.delimiter           = delimiter.encode('utf-8')
        self.max_length          = max_length
        self.connections = {}
        self.use("calvinsys.network.serverhandler", shorthand="server")

    def will_migrate(self):
        self['server'].stop()

    def did_migrate(self):
        self.server = None

    @stateguard(lambda self: not self.host and not self.port and not self.server)
    @condition(['host', 'port'], [])
    def setup(self, host, port):
        self.host = host
        self.port = port


    @stateguard(lambda self: self.host and self.port and not self.server)
    @condition()
    def start(self):
        try:
            self.server = self['server'].start(self.host, self.port, self.mode, self.delimiter, self.max_length)
        except Exception as e:
            _log.exception(e)


    @stateguard(lambda self: self.server and self.server.connection_pending())
    @condition()
    def accept(self):
        addr, conn = self.server.accept()
        self.connections[addr] = conn


    @stateguard(lambda self: self.connections)
    @condition(['handle', 'token'])
    def send(self, handle, token):
        for h, c in self.connections.items():
            if h == handle:
                self.server.send(c, token.encode('utf-8'))

    @stateguard(lambda self: self.connections and any([c.data_available for c in self.connections.values()]))
    @condition([], ['handle', 'token'])
    def receive(self):
        for h, c in self.connections.items():
            if c.data_available:
                data = self.server.receive(c)
                break
        return (h, data)

    @stateguard(lambda self: self.connections and any([c.connection_lost for c in self.connections.values()]))
    @condition()
    def close(self):
        for handle, connection in self.connections.items():
            if connection.connection_lost:
                connection.connection_lost = False
                del self.connections[handle]
                break

    action_priority = (accept, receive, send, close, setup, start)
    requires = ['calvinsys.network.serverhandler']


    test_set = [
        {
            'input': {'host': [],
                      'port': [],
                      'handle': [],
                      'token': []},
            'output': {'handle': [],
                       'token': []}
        }
    ]
