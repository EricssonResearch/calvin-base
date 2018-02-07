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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib, calvinsys

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
        self.cc = calvinsys.open(self, "network.socketclient", address=self.address, port=self.port, connection_type="TCP")

    def will_migrate(self):
        if self.cc:
            calvinsys.close(self.cc)

    def did_migrate(self):
        self.setup()
        if self.address is not None:
            self.connect()

    def setup(self):
        self.regexp = calvinlib.use('regexp')

    @stateguard(lambda self: self.cc and calvinsys.can_write(self.cc))
    @condition(action_input=['data_in'])
    def send(self, token):
        if isinstance(token, basestring):
            token = str(token)
            calvinsys.write(self.cc, token)
        else:
            _log.error("Error token must be string or unicode, token is %s", repr(token))

    @stateguard(lambda self: self.cc and calvinsys.can_read(self.cc))
    @condition(action_output=['data_out'])
    def receive(self):
        data = calvinsys.read(self.cc)
        return (data,)

    # URI parsing - 0: protocol, 1: address, 2: :port
    URI_REGEXP = r'([^:]+)://([^/:]*)(:[0-9]+)'

    @condition(action_input=['control_in'])
    def control(self, control):
        if control['control'] == 'connect' and not self.cc:
            self._new_connection(control)
        elif control['control'] == 'disconnect' and self.cc:
            self._close_connection()

    def _new_connection(self, control):
        uri = self.regexp.findall(self.URI_REGEXP, control['uri'])
        uri_parts = uri[0]
        protocol = uri_parts[0]

        if protocol != 'tcp':
            _log.warn("Protocol '%s' not suuported" % (protocol,))
        else:
            self.address = uri_parts[1]
            self.port = int(uri_parts[2][1:])
            self.connect()

    def _close_connection(self):
        calvinsys.close(self.cc)
        self.cc = None

    def exception_handler(self, action, args):
        """Handler ExceptionTokens"""
        self.EOST_token_received = True

    action_priority = (control, receive, send)
    requires = ['network.socketclient', 'regexp']


    test_set = [
        {
            'input': {'data_in': [],
                      'control_in': []},
            'output': {'data_out': []}
        }
    ]
