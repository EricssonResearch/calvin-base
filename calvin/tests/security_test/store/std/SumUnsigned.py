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


class SumUnsigned(Actor):

    """
    Read a number and compute a cumulative sum
    Inputs:
      integer : Number
    Outputs:
      integer : Cumulative sum
    """
    @manage(['sum'])
    def init(self):
        self.sum = 0

    @condition(['integer'], ['integer'])
    def sum(self, input):
        self.sum = self.sum + input
        return ActionResult(production=(self.sum, ))

    action_priority = (sum, )

    test_set = [
        {
            'in': {'integer': [5]},
            'out': {'integer': [5]},
            'postcond': [lambda self: self.sum == 5]
        },
        {
            'in': {'integer': [1, 2, 3]},
            'out': {'integer': [6, 8, 11]},
            'postcond': [lambda self: self.sum == 11]
        }
    ]
