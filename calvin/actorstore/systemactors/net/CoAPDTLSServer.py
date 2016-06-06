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


class CoAPDTLSServer(Actor):
    """
    Listen for CoAP messages on a given port.

    Input:
      host : IP address to listen on
      port : port to listen on
    Output:
      data_out : Data received in POST requests as tokens.
    """

    @manage(['port'])
    def init(self, objectsecurity=False):
	self.host = None
        self.port = None
        self.listener = None
        self.started = False
        self.setup(objectsecurity)

    def listen(self):
        self.listener = self['server'].start(self.host, self.port)
	self.started = True

    def did_migrate(self):
        self.setup()
        if self.port is not None:
            self.listen()

    def setup(self, objectsecurity):
	if objectsecurity: 
            self.use('calvinsys.network.coapdtlsosserverhandler', shorthand='server')
	else:
            self.use('calvinsys.network.coapdtlsserverhandler', shorthand='server')

    @condition(action_input=['host', 'port'])
    def new_port(self, host, port):
	if not (self.port == port and self.host == host):
	    self.host = host
	    self.port = port
            self.listen()
        return ActionResult()

    @condition(action_output=['data_out'])
    @guard(lambda self: self.started and self['server'].data_available())
    def receive_data(self):
        data = self['server'].get_data()
	
        return ActionResult(production=(data,))

    action_priority = (new_port, receive_data)
    requires = ['calvinsys.network.coapdtlsserverhandler', 'calvinsys.network.coapdtlsosserverhandler']
