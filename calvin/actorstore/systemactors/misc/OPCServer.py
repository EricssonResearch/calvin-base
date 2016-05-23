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

from calvin.actor.actor import Actor, ActionResult, manage, condition

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class OPCServer(Actor):
    """
    An OPC Server.
    
    Input:
        operation: struct with variable name, and new value, or omit for read
    Output:
        result: struct containing current value,
    """

    @manage([]) 
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()
 
    def will_migrate(self):
        self['opc'].stop()
        
    def setup(self):
        self.use('calvinsys.opcua.server', shorthand='opc')
        self['opc'].start()

    @condition(action_input=['operation'], action_output=['result'])
    def next_operation(self, operation):
        obj, var = operation['variable'].split(".")
        if operation.get('value', None) is not None:
            val = operation['value']
            self['opc'].set_value(obj, var, val)
        else :
            val = self['opc'].get_value(obj, var)
        operation["value"] = val
        return ActionResult(production=(operation,))

    action_priority = (next_operation,)
    requires = ['calvinsys.opcua.server']
