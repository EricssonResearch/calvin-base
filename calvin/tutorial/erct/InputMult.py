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

from calvin.actor.actor import Actor, condition, ActionResult


class InputMult(Actor):
    """
        Multiplies input on port 'argument' by input in port 'multiplier'
        Inputs :
          multiplier : a multiplier
          argument : an integer
        Output :
          result : the result
    """
    def init(self):
        pass

    @condition(action_input=['multiplier', 'argument'], action_output=['result'])
    def multiply(self, multiplier, argument):
        result = multiplier * argument
        return ActionResult(production=(result, ))

    action_priority = (multiply, )
