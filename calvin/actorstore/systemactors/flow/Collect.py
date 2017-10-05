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


class Collect(Actor):
    """
    Collect tokens from many ports on the inport
    Inputs:
      token(routing="collect-unordered") : collecting token stream
    Outputs:
        token : resulting token stream
    """

    def init(self):
        pass

    @condition(['token'], ['token'])
    def collect(self, input):
        return (input, )

    action_priority = (collect,)

    test_args = []

    test_set = [
        {
            'inports': {'token': [1, 2, 'a', 'b']},
            'outports': {'token': [1, 2, 'a', 'b']}
        },
        {
            'inports': {'token': [2]},
            'outports': {'token': [2]}
        }
    ]
