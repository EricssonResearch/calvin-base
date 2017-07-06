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

from calvin.actor.actor import Actor, condition


class Join(Actor):
    """
    Join two streams of tokens. Deprecated.
    
    Note: This actor gives preference to token_1, hence if there is
    always a token available on that port, then token_2 will starve.
    The actor you are looking for is probably flow.Collect or possibly
    flow.Alternate2
    
    Inputs:
      token_1 : first token stream
      token_2 : second token stream
    Outputs:
        token : resulting token stream
    """

    def init(self):
        pass

    @condition(['token_1'], ['token'])
    def port_one(self, input):
        return (input, )

    @condition(['token_2'], ['token'])
    def port_two(self, input):
        return (input, )

    action_priority = (port_one, port_two)

    test_args = []

    test_set = [
        {
            'in': {'token_1': [1, 2], 'token_2': ['a', 'b']},
            'out': {'token': [1, 2, 'a', 'b']}
        },
        {
            'in': {'token_2': [2]},
            'out': {'token': [2]}
        }
    ]
