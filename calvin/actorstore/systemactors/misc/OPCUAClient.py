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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class OPCUAClient(Actor):
    """
    An OPCUA Client. Connects to given OPCUA server and sets up subscriptions everything it can find in the supplied namespace.
    
    Output:
        variable : {
                      "Status": {
                        "Doc": <human readable description of status code>,
                        "Code": <status code>,
                        "Name": <name of status code>
                        },                                        
                      "Name": <name of variable>,
                      "ServerTimestamp": <server timestamp>,
                      "SourceTimestamp": <source timestamp>,
                      "Value": <variable value>,
                      "Type": <type of variable (or contents for compound variables)>,
                      "Id": <id of variable>
                    }
    

    """

    @manage(['server_settings']) 
    def init(self, endpoint, namespace):
        self.server_settings = {"endpoint": endpoint, "namespace": namespace}
        self.setup()

    def did_migrate(self):
        self.setup()
 
    def will_migrate(self):
        self['opcua'].shutdown()
        
    def setup(self):
        self.use('calvinsys.opcua.client', shorthand='opcua')
        self['opcua'].startup(self.server_settings)

    @condition(action_output=['variable'])
    @guard(lambda self: self['opcua'].variable_changed)
    def changed(self):
        variable = self['opcua'].get_first_changed()
        return ActionResult(production=(variable,))

    action_priority = (changed,)
    requires = ['calvinsys.opcua.client']
