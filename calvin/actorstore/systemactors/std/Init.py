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

# encoding: utf-8

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard

class Init(Actor):

    """
    Insert an initial token (data) before passing all others through

    Inputs:
      in: Any token
    Outputs:
      out: Data given as parameter followed by data from in port
    """

    @manage(['done', 'data'])
    def init(self, data):
        self.done = False
        self.data = data

    @condition([], ['out'])
    @guard(lambda self: not self.done)
    def initial_action(self):
        self.done = True
        return ActionResult(production=(self.data,))

    @condition(['in'], ['out'])
    @guard(lambda self, data: self.done)
    def passthrough(self, data):
        return ActionResult(production=(data,))

    action_priority = (passthrough, initial_action)

    test_args = [0]

    test_set = [
        {
            'in': {'in': [1,2,3]},
            'out': {'out': [0,1,2,3]},
        },
    ]
