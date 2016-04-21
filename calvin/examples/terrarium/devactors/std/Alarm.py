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

from calvin.actor.actor import Actor, ActionResult, condition


class Alarm(Actor):
    """
    Checks whether field value is within [lower, upper]
    Inputs:
      dict : dict of the form { "value": <value>, "lower": <lower>, "upper": <upper>}
    Outputs:
      warning: True iff value outside of range lower .. upper
    """

    def init(self):
        pass

    @condition(action_input=["dict"], action_output=["warning"])
    def check(self, container):
        val = container.get("value", 0)
        lower = container.get("lower", 0)
        upper = container.get("upper", 0)
        result = val > upper or val < lower
        return ActionResult(production=(result,))

    action_priority = (check, )
