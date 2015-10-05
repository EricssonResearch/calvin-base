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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class TCPClient(Actor):
    """
    Etablish a TCP connection and forward all tokens.
    Any recevied data on the TCP connection is forwarded according to protocol.

    Input:
      data_in : Each received token will be sent out through the TCP connection.
      control_in : Each received token will be sent out through the TCP connection.
    Output:
      data_out : Data received on the TCP connection will be sent as tokens.
    """

    @manage(['address', 'port', 'mode', 'delimiter'])
    def init(self, mode="delimiter", delimiter="\r\n"):
        self.address = None
        self.port = None
        self.EOST_token_received = False
        self.cc = None
        self.mode = mode
        self.delimiter = delimiter
        self.setup()

        if self.address is not None:
            self.connect()

    def connect(self):
        self.cc = self['socket'].connect(self.address, self.port, mode=self.mode, delimiter=self.delimiter)

    def will_migrate(self):
        if self.cc:
            self.cc.disconnect()

    def did_migrate(self):
        self.setup()
        if self.address is not None:
            self.connect()

    def setup(self):
        self.use('calvinsys.network.socketclienthandler', shorthand='socket')
        self.use('calvinsys.native.python-re', shorthand='regexp')

    @condition(action_input=['data_in'])
    @guard(lambda self, token: self.cc and self.cc.is_connected())
    def send(self, token):
        self.cc.send(token)
        return ActionResult(production=())

    @condition(action_output=['data_out'])
    @guard(lambda self: self.cc and self.cc.is_connected() and self.cc.have_data())
    def receive(self):
        data = self.cc.get_data()
        return ActionResult(production=(data,))

    # URI parsing - 0: protocol, 1: address, 2: :port
    URI_REGEXP = r'([^:]+)://([^/:]*)(:[0-9]+)'

    @condition(action_input=['control_in'])
    @guard(lambda self, control: control['control'] == 'connect' and not self.cc)
    def new_connection(self, control):
        uri = self['regexp'].findall(self.URI_REGEXP, control['uri'])
        uri_parts = uri[0]
        protocol = uri_parts[0]

        if protocol != 'tcp':
            _log.warn("Protocol '%s' not suuported" % (protocol,))
        else:
            self.address = uri_parts[1]
            self.port = int(uri_parts[2][1:])
            self.connect()

        return ActionResult(production=())

    @condition(action_input=['control_in'])
    @guard(lambda self, control: control['control'] == 'disconnect' and self.cc)
    def close_connection(self, control):
        self.cc.disconnect()
        self.cc = None
        return ActionResult(production=())

    def exception_handler(self, action, args, context):
        """Handler ExceptionTokens"""
        self.EOST_token_received = True
        return ActionResult(production=())

    action_priority = (new_connection, close_connection, receive, send)
    requires = ['calvinsys.network.socketclienthandler', 'calvinsys.native.python-re']
