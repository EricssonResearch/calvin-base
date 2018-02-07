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


class UDPSender(Actor):
    """
    Send all incoming tokens to given address/port over UDP

    Control port takes control commands of the form (uri only applicable for connect.)

        {
            "command" : "connect"/"disconnect",
            "uri": "udp://<address>:<port>"
        }


    Input:
      data_in : Each received token will be sent to address set via control port
      control_in : Control port
    """

    @manage(['address', 'port'])
    def init(self):
        self.address = None
        self.port = None
        self.sender = None
        self.setup()

    def connect(self):
        if self.sender:
            calvinsys.close(self.sender)
        self.sender = calvinsys.open(self, "network.socketclient", address=self.address, port=self.port, connection_type="UDP")

    def will_migrate(self):
        if self.sender:
            calvinsys.close(self.sender)

    def did_migrate(self):
        self.setup()
        if self.address is not None:
            self.connect()

    def setup(self):
        self.regexp = calvinlib.use('regexp')

    @stateguard(lambda self: self.sender and calvinsys.can_write(self.sender))
    @condition(action_input=['data_in'])
    def send(self, token):
        calvinsys.write(self.sender, token)

    # URI parsing - 0: protocol, 1: host, 2: port
    URI_REGEXP = r'([^:]+)://([^/:]*):([0-9]+)'

    def parse_uri(self, uri):
        status = False
        try:
            parsed_uri = self.regexp.findall(self.URI_REGEXP, uri)[0]
            protocol = parsed_uri[0]
            if protocol != 'udp':
                _log.warn("Protocol '%s' not supported, assuming udp" % (protocol,))
            self.address = parsed_uri[1]
            self.port = int(parsed_uri[2])
            status = True
        except:
            _log.warn("malformed or erroneous control uri '%s'" % (uri,))
            self.address = None
            self.port = None
        return status

    @condition(action_input=['control_in'])
    def control(self, control):
        cmd = control.get('command', '')
        if cmd == 'connect' and self.sender is None:
            self._new_connection(control)
        elif cmd == 'disconnect' and self.sender is not None:
            self._close_connection()

    def _new_connection(self, control):
        if self.parse_uri(control.get('uri', '')):
            self.connect()

    def _close_connection(self):
        calvinsys.close(self.sender)
        self.sender = None

    action_priority = (control, send)
    requires = ['network.socketclient', 'regexp']


    test_set = [
        {
            'input': {'data_in': [],
                      'control_in': []}
        }
    ]
