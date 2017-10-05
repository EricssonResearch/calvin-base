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

from calvin.actor.actor import Actor, condition, stateguard, manage


class Dealternate2(Actor):
    """
    Split token stream into two streams of tokens (odd and even tokens)
    Inputs:
      token : incoming token stream
    Outputs:
      token_1 : first token stream
      token_2 : second token stream
    """

    @manage(['is_even_token'])
    def init(self):
        self.is_even_token = True

    def is_even(self):
        return self.is_even_token

    def is_odd(self):
        return not self.is_even_token

    @stateguard(is_even)
    @condition(['token'], ['token_1'])
    def port_one(self, tok):
        self.is_even_token = False
        return (tok, )

    @stateguard(is_odd)
    @condition(['token'], ['token_2'])
    def port_two(self, tok):
        self.is_even_token = True
        return (tok, )

    action_priority = (port_one, port_two)

    test_set = [
        {
            'inports': {'token': [1, 'a', 2, 'b']},
            'outports': {'token_1': [1, 2], 'token_2': ['a', 'b']}
        },
    ]
