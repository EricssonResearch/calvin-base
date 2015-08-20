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

from calvin.actor.actor import Actor, ActionResult, manage, condition


class Counter(Actor):
    """
    Produce next integer in a sequence 1,2,3,...
    Outputs:
      integer : Integer
    """

    @manage(['count'])
    def init(self):
        self.count = 0

    @condition(action_output=['integer'])
    def cnt(self):
        self.count += 1
        return ActionResult(production=(self.count, ))

    action_priority = (cnt,)

    def report(self):
        return self.count

    test_args = []
    test_set = [
        {'in': {}, 'out': {'integer': [n]}} for n in range(1, 10)
    ]
