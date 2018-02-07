# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class SimpleUDPSender(Actor):
    """
    Send all incoming tokens to given address/port over UDP

    Input:
      data : Each received token will be sent to address set via control port
    """

    @manage(['address', 'port'])
    def init(self, address, port):
        self.address = address
        self.port = port
        self.sender = None
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.sender = calvinsys.open(self, "network.socketclient", address=self.address, port=self.port, connection_type="UDP")

    @stateguard(lambda self: self.sender and calvinsys.can_write(self.sender))
    @condition(action_input=['data'])
    def send(self, token):
        calvinsys.write(self.sender, token)

    action_priority = (send, )
    requires = ['network.socketclient']


#    TBD: Reenable test after updating to use new calvinsys API
#    test_kwargs = {'address': '123.45.67.8', 'port': 9999}
#    test_set = [
#        {
#            'input': {'data': ['dummy']}
#        }
#    ]
