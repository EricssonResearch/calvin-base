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

from calvin.actor.actor import Actor, manage, condition, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class SimpleUDPListener(Actor):
    """
    Listen for UDP messages on a given port. Address is of the form "ip:port" (note: ip is ipv4)

    Output:
      data : data in packets received on the UDP port will forwarded as tokens.
    """

    @manage(['host', 'port'])
    def init(self, address):
        self.host, self.port = address.split(':')
        try:
            self.port = int(self.port)
        except ValueError:
            self.port = 0

        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.use('calvinsys.network.serverhandler', shorthand='server')
        self.listener = self['server'].start(self.host, self.port, "udp")

    @stateguard(lambda self: self.listener and self.listener.have_data())
    @condition(action_output=['data'])
    def receive(self):
        message = self.listener.data_get()
        return (message["data"],)

    action_priority = (receive,)
    requires = ['calvinsys.network.serverhandler']


#    TBD: Reenable test after updating to use new calvinsys API
#    test_kwargs = {'address': '123.45.67.8:9999'}
#    test_set = [
#        {
#            'output': {'data': []}
#        }
#    ]
