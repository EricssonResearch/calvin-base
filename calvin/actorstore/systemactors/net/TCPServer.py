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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys
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

    def will_migrate(self):
        calvinsys.close(self.server)

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
            self.server = calvinsys.open(self,
                'network.tcpserver',
                host=self.host,
                port=self.port,
                mode=self.mode,
                delimiter=self.delimiter,
                max_length=self.max_length)
        except Exception as e:
            _log.exception(e)

    @stateguard(lambda self: self.server and calvinsys.can_read(self.server))
    @condition([], ['handle', 'token'])
    def receive(self):
        data = calvinsys.read(self.server)
        return (data["handle"], data["data"])

    @stateguard(lambda self: self.server and calvinsys.can_write(self.server))
    @condition(['handle', 'token'])
    def send(self, handle, token):
        calvinsys.write(self.server, {"handle": handle, "data": token.encode('utf-8')})

    action_priority = (receive, send, setup, start)
    requires = ['network.tcpserver']

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
