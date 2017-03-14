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

from calvin.actor.actor import Actor, manage, condition, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class OPCUASubscriber(Actor):
    """
    An OPCUA Client. Connects to given OPCUA server and sets up subscriptions for given node id's
    nodeids are of the form ns=<#>;s=<string>.

        {
          "Status": {
            "Doc": <human readable description of status code>,
            "Code": <status code>,
            "Name": <name of status code>
            },
          "Name": <name of variable>,
          "ServerTimestamp": <server timestamp>,
          "SourceTimestamp": <source timestamp>,
          "CalvinTimestamp": <local timestamp>
          "Value": <variable value>,
          "Type": <type of variable (or contents for compound variables)>,
          "Id": <id of variable>
        }

    Output:
        variable :
    """

    @manage(['endpoint', 'nodeids'])
    def init(self, endpoint, nodeids):
        self.endpoint = endpoint
        self.nodeids = [ str(nodeid) for nodeid in nodeids]
        self.setup()

    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        self['opcua'].stop_subscription()

    def will_end(self):
        self['opcua'].shutdown()

    def setup(self):
        self.use('calvinsys.opcua.client', shorthand='opcua')
        self['opcua'].start_subscription(self.endpoint, self.nodeids)

    @stateguard(lambda self: self['opcua'].variable_changed)
    @condition(action_output=['variable'])
    def changed(self):
        variable = self['opcua'].get_first_changed()
        return (variable,)

    action_priority = (changed,)
    requires = ['calvinsys.opcua.client']
