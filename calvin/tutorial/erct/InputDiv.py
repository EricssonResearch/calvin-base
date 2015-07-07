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

from calvin.actor.actor import Actor, condition, guard, ActionResult
from calvin.runtime.north.calvin_token import ExceptionToken


class InputDiv(Actor):

    """
      Divides input on port 'dividend' with input on port 'divisor'
      Inputs :
        dividend : integer
        divisor : integer
      Output :
        result : an integer
    """

    def init(self):
        pass

    @condition(action_input=[('dividend', 1), ('divisor', 1)], action_output=[('result', 1)])
    @guard(lambda self, n, d: d != 0)
    def divide(self, numerator, denumerator):
        result = numerator / denumerator
        return ActionResult(production=(result,))

    @condition(action_input=[('dividend', 1), ('divisor', 1)], action_output=[('result', 1)])
    @guard(lambda self, n, d: d == 0)
    def divide_by_zero(self, numerator, denumerator):
        result = ExceptionToken("Division by 0")
        return ActionResult(production=(result,))

    action_priority = (divide_by_zero, divide)
