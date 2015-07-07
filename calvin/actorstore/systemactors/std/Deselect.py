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


class Deselect(Actor):
    """
    Route token from 'true' or 'false' to 'data' port depending on 'select'

    Deselect assumes 0 (false) or 1 (true) as input, values outside that
    range will default to 'false'.

    Inputs:
      false  : Token to output 'data' if select token is 0
      true   : Token to output 'data' if select token is 1
      select : Select which inport will propagate to 'data' port
    Outputs:
      data  : Token from 'true' or 'false' port
    """
    @manage([])
    def init(self):
        pass

    @condition(['select', 'false'], ['data'])
    @guard(lambda self, select, data : select == 0)
    def false_action(self, select, data):
        return ActionResult(production=(data, ))

    @condition(['select', 'true'], ['data'])
    @guard(lambda self, select, data : select == 1)
    def true_action(self, select, data):
        return ActionResult(production=(data, ))

    @condition(['select', 'false'], ['data'])
    @guard(lambda self, select, data : select not in [0, 1])
    def invalid_select_action(self, select, data):
        # Default to false if select value is not 0 or 1
        return ActionResult(production=(data, ))


    action_priority = (false_action, true_action, invalid_select_action)

