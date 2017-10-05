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

from calvin.actor.actor import Actor, manage, condition, stateguard


class Switch(Actor):
    """
    Switch data paths depending on 'switch'

    Switch assumes 'false' or 'true' as input to 'switch', other values are considered 'false'.

    Inputs:
      switch : Switch data paths a->b, b->a if 'true, else a->a, b->b
      a : token
      b : token
    Outputs:
      a : token
      b : token
    """
    @manage([])
    def init(self):
        pass

    @condition(['switch', 'a', 'b'], ['a', 'b'])
    def action(self, switch, a, b):
        # Default to false if select value is not true or false
        if switch is True:
            a, b = b, a
        return (a, b )

    action_priority = (action,)

    test_set = [
        {
            'inports': {'switch': [True, False, 0, 1], 'a':[1,2,3,4], 'b':['a','b','c','d']},
            'outports': {'a':['a',2,3,4], 'b':[1,'b','c','d']},
        },
    ]
