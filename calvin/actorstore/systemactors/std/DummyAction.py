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


class DummyAction(Actor):

    """
    Propagate a token
    Input:
        token : any token
    Output:
        token : any token
    """

    @manage()
    def init(self):
        pass

    def is_even(self, input):
        return ((input if isinstance(input, (int, long)) else 0) % 2) == 0

    def is_odd(self, input):
        return not self.is_even(input)

    @condition(['token'], ['token'])
    @guard(is_even)
    def dummy_action(self, input):
        return ActionResult(production=(input, ))

    @condition(['token'], ['token'])
    @guard(is_odd)
    def verbose_action(self, input):
        return ActionResult(production=("(" + str(input) + ")", ))

    action_priority = (dummy_action, verbose_action)

    test_set = [
        {
            'in': {'token': [i]},
            'out': {'token': [i if i % 2 == 0 else '(%s)' % (i, )]}
        } for i in range(10)
    ]
