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


class Select(Actor):
    """
    Route 'data' token to 'case_true' or 'case_false' port depending on 'select'

    Select assumes 0 (false) or 1 (true) as input, values outside that
    range will default to 'case_false'.

    Inputs:
      select : Select output for token on 'data' port
      data  : Token to send to 'case_true' or 'case_false' port
    Outputs:
      case_false  : Token from input 'data' if select token is 0
      case_true   : Token from input 'data' if select token is 1
    """
    @manage([])
    def init(self):
        pass

    @condition(['select', 'data'], ['case_false'])
    @guard(lambda self, select, data: select == 0)
    def false_action(self, select, data):
        return ActionResult(production=(data, ))

    @condition(['select', 'data'], ['case_true'])
    @guard(lambda self, select, data: select == 1)
    def true_action(self, select, data):
        return ActionResult(production=(data, ))

    @condition(['select', 'data'], ['case_false'])
    @guard(lambda self, select, data: select not in [0, 1])
    def invalid_select_action(self, select, data):
        # Default to false if select value is not 0 or 1
        return ActionResult(production=(data, ))

    action_priority = (false_action, true_action, invalid_select_action)
