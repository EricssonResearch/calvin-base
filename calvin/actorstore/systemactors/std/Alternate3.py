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

from calvin.actor.actor import Actor, ActionResult, condition, guard, manage


class Alternate3(Actor):
    """
    Alternating between three streams of tokens
    Inputs:
      token_1 : first token stream
      token_2 : second token stream
      token_3 : third token stream
    Outputs:
        token : resulting token stream
    """

    @manage(['next_port'])
    def init(self):
        self.next_port = 1

    @condition(['token_1'], ['token'])
    @guard(lambda self, _: self.next_port == 1)
    def port_1(self, data):
        self.next_port = 2
        return ActionResult(production=(data, ))

    @condition(['token_2'], ['token'])
    @guard(lambda self, _: self.next_port == 2)
    def port_2(self, data):
        self.next_port = 3
        return ActionResult(production=(data, ))

    @condition(['token_3'], ['token'])
    @guard(lambda self, _: self.next_port == 3)
    def port_3(self, data):
        self.next_port = 1
        return ActionResult(production=(data, ))

    action_priority = (port_1, port_2, port_3)

    test_set = [
        {
            'in': {'token_1': [1], 'token_2': ['a'], 'token_3': ['alpha']},
            'out': {'token': [1, 'a', 'alpha']}
        },
        {
            'in': {'token_1': [1]},
            'out': {'token': [1]}
        }
    ]
