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

import random
from calvin.actor.actor import Actor, ActionResult, manage, condition


class Random(Actor):
    """
    Produce random integer in range [minimum ... maximum]

    Inputs:
      trigger : Any token
    Outputs:
      integer : Random integer in range [minimum ... maximum]
    """

    @manage(['min', 'max'])
    def init(self, minimum, maximum):
        self.min = minimum
        self.max = maximum

    @condition(action_input=['trigger'], action_output=['integer'])
    def action(self, trigger):
        n = random.randint(self.min, self.max)
        return ActionResult(production=(n, ))

    action_priority = (action,)

    def report(self):
        return self.count

