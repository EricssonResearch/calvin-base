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


class UDPListener(Actor):
    """
    Listen for UDP messages on a given port.

    Control port takes control commands of the form (uri only applicable for connect.)

    {
        "command" : "connect"/"disconnect",
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
        self.listener = self['server'].start(self.host, self.port, "udp")

    def did_migrate(self):
        self.setup()
        if self.port is not None:
            self.listen()

    def setup(self):
        self.use('calvinsys.network.serverhandler', shorthand='server')
        self.use('calvinsys.native.python-re', shorthand='regexp')

    @condition(action_output=['data_out'])
    @guard(lambda self: self.listener and self.listener.have_data())
    def receive(self):
        data = self.listener.data_get()
        return ActionResult(production=(data,))

    # URI parsing - 0: protocol, 1: host, 2: port
    URI_REGEXP = r'([^:]+)://([^/:]*):([0-9]+)'

    def parse_uri(self, uri):
        status = False
        try:
            parsed_uri = self['regexp'].findall(self.URI_REGEXP, uri)[0]
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
    @guard(lambda self, control: control.get('command', '') == 'listen' and not self.listener)
    def new_port(self, control):
        if self.parse_uri(control.get('uri', '')):
            self.listen()
        return ActionResult()

    @condition(action_input=['control_in'])
    @guard(lambda self, control: control.get('command', '') == 'stop' and self.listener)
    def close_port(self, control):
        self.listener.stop()
        del self.listener
        self.listener = None
        return ActionResult(production=())

    action_priority = (new_port, close_port, receive)
    requires = ['calvinsys.network.serverhandler', 'calvinsys.native.python-re']
