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


class UDPListener(Actor):
    """
    Listen for UDP messages on a given port.

    Control port takes control commands of the form (uri only applicable for connect.)

        {
            "command" : "listen"/"stop",
            "uri": "udp://<ipv4 address>:<port>"
        }


    Input:
      control_in : JSON containing host & port to listen to.
    Output:
      data_out : Data received on the UDP port will be sent as tokens.
    """

    @manage(['host', 'port'])
    def init(self):
        self.host = None
        self.port = None
        self.listener = None
        self.setup()

    def listen(self):
        self.listener = calvinsys.open(self, "network.udplistener", host=self.host, port=self.port)

    def did_migrate(self):
        self.setup()
        if self.port is not None:
            self.listen()

    def setup(self):
        self.regexp = calvinlib.use('regexp')

    @stateguard(lambda self: self.listener and calvinsys.can_read(self.listener))
    @condition(action_output=['data_out'])
    def receive(self):
        data = calvinsys.read(self.listener)
        return (data,)

    # URI parsing - 0: protocol, 1: host, 2: port
    URI_REGEXP = r'([^:]+)://([^/:]*):([0-9]+)'

    def parse_uri(self, uri):
        status = False
        try:
            parsed_uri = self.regexp.findall(self.URI_REGEXP, uri)[0]
            protocol = parsed_uri[0]
            if protocol != 'udp':
                _log.warn("Protocol '%s' not supported, assuming udp" % (protocol,))
            self.host = parsed_uri[1]
            self.port = int(parsed_uri[2])
            status = True
        except:
            _log.warn("malformed or erroneous control uri '%s'" % (uri,))
            self.host = None
            self.port = None
        return status

    @condition(action_input=['control_in'])
    def control(self, control):
        if control.get('command', '') == 'listen' and not self.listener:
            self._new_port(control)
        elif control.get('command', '') == 'stop' and self.listener:
            self._close_port()

    def _new_port(self, control):
        if self.parse_uri(control.get('uri', '')):
            self.listen()

    def _close_port(self):
        calvinsys.close(self.listener)
        self.listener = None

    action_priority = (control, receive)
    requires = ['network.udplistener', 'regexp']


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
