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
from calvin.runtime.north.calvin_token import EOSToken

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class SocketClient(Actor):
    """
    Etablish a TCP/UDP connection and forward all tokens.
    Any recevied data on the TCP/UDP connection is forwarded according to protocol.

    Input:
      inData    : Each received token will be sent out through the TCP/UDP connection.
      inControl : Each received token will be sent out through the TCP/UDP connection.
    Output:
      outData    : Data received on the TCP/UDP connection will be sent as tokens.
      outControl : Data received on the TCP/UDP connection will be sent as tokens.
    """

    @manage(['address', 'port', 'protocol', 'type_', 'delimiter'])
    def init(self, address=None, port=None, protocol='raw', type_="TCP", delimiter='\r\n'):
        self.address = address
        self.port = port
        self.protocol = protocol
        self.type_ = type_
        self.delimiter = delimiter
        self.EOST_token_received = False
        self.cc = None
        self.use('calvinsys.io.socketclienthandler', shorthand='socket')

        # Connect
        if address is not None:
            self.connect()

    def connect(self):
        self.cc = self['socket'].connect(self.address, self.port, self.protocol, self.type_, self.delimiter)

    def will_migrate(self):
        self.cc.disconnect()

    def did_migrate(self):
        self.connect()

    @condition(action_input=['inData'])
    @guard(lambda self, token: self.cc and self.cc.is_connected())
    def send(self, token):
        self.cc.send(token)
        return ActionResult(production=())

    @condition(action_output=['outData'])
    @guard(lambda self: self.cc and self.cc.is_connected() and self.cc.have_data())
    def receive(self):
        data = self.cc.get_data()
        return ActionResult(production=(data,))

    @condition(action_input=['inControl'])
    @guard(lambda self, token: True)
    def receive_control(self, token):
        if token[0] == "connect":
            if not self.cc:
                # TODO: validate these
                self.address = token[1]['addr']
                self.port = token[0]['port']
                self.connect()
        if token[0] == "disconnect":
            if self.cc:
                self.cc.disconnect()
                self.cc = None
        return ActionResult(production=())

    @condition(action_output=['outControl'])
    @guard(lambda self: self.cc and self.cc.have_control())
    def send_control(self):
        data = self.cc.get_control()
        return ActionResult(production=(data,))

    def exception_handler(self, action, args, context):
        """Handler ExceptionTokens"""
        self.EOST_token_received = True
        return ActionResult(production=())

    action_priority = (receive_control, receive, send, send_control)
    requires = ['calvinsys.io.socketclienthandler']
