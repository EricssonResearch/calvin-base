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
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken
from copy import copy

class Iterate(Actor):

    """
    Produce sequence of items by iterating over 'token',
    or simply pass 'token' along if not iterable (i.e. list, dict, or string)

    N.B. Empty iterables produces a 'null' token.

    FIXME: Is 'null' production the right thing? Exception? Nothing?

    Inputs:
      token: any token
    Outputs:
      item: item (or value if input is dictionary)
      index: index of item (or key if input is dictionary)
    """


    @manage(['data', 'has_data', 'index'])
    def init(self):
        self.data = None
        self.has_data = False
        self.index = 0

    @condition(['token'], [])
    @guard(lambda self, data: not self.has_data and (type(data) is list or type(data) is dict))
    def consume_mutable(self, data):
        if not data:
            # Empty list => null output
            self.data = None
        else:
            self.data = copy(data)
        self.has_data = True
        self.index = 0
        return ActionResult()

    @condition(['token'], [])
    @guard(lambda self, data: not self.has_data)
    def consume_immutable(self, data):
        if data == "":
            # Empty string => null output
            self.data = None
        else:
            self.data = data
        self.has_data = True
        self.index = 0
        return ActionResult()


    @condition([], ['item', 'index'])
    @guard(lambda self: self.has_data and type(self.data) is list)
    def produce_listitem(self):
        res = self.data.pop(0)
        i = self.index
        self.index += 1
        if not self.data:
            self.data = None
            self.has_data = False
        return ActionResult(production=(res, i))

    @condition([], ['item', 'index'])
    @guard(lambda self: self.has_data and type(self.data) is dict)
    def produce_dictitem(self):
        k, v = self.data.popitem()
        if not self.data:
            self.data = None
            self.has_data = False
        return ActionResult(production=(v, k))

    @condition([], ['item', 'index'])
    @guard(lambda self: self.has_data and isinstance(self.data, basestring))
    def produce_stringitem(self):
        res = self.data[0]
        self.data = self.data[1:]
        i = self.index
        self.index += 1
        if not self.data:
            self.data = None
            self.has_data = False
        return ActionResult(production=(res, i))

    @condition([], ['item', 'index'])
    @guard(lambda self: self.has_data)
    def produce_plainitem(self):
        res = self.data
        self.data = None
        self.has_data = False
        return ActionResult(production=(res, 0))



    action_priority = (produce_listitem, produce_dictitem, produce_stringitem, produce_plainitem, consume_mutable, consume_immutable)

    test_args = []
    test_kwargs = {}

    test_set = [
        {
            'in': {'token': [[1,2,3]]},
            'out': {'item': [1,2,3], 'index': [0, 1, 2]},
        },
        {
            'in': {'token': ["abcd"]},
            'out': {'item': ["a", "b", "c", "d"], 'index': [0, 1, 2, 3]},
        },
        {
            'in': {'token': [1,2,3]},
            'out': {'item': [1, 2, 3], 'index': [0, 0, 0]},
        },
        {
            'in': {'token': {"a":"A", "b":1}},
            'out': {'item': set([1, "A"]), 'index': set(["a", "b"])},
        },
        {
            'in': {'token': [""]},
            'out': {'item': [None], 'index': [0]},
        },
        {
            'in': {'token': [{}]},
            'out': {'item': [None], 'index': [0]},
        },
        {
            'in': {'token': [[]]},
            'out': {'item': [None], 'index': [0]},
        },
        {
            'in': {'token': [[], []]},
            'out': {'item': [None, None], 'index': [0, 0]},
        },

        {
            'in': {'token': [[1], [2]]},
            'out': {'item': [1, 2], 'index': [0, 0]},
        },
        {
            'in': {'token': [[], [1,2,3]]},
            'out': {'item': [None, 1,2,3], 'index': [0, 0, 1, 2]},
        },
        {
            'in': {'token': [[], [], [1,2]]},
            'out': {'item': [None, None, 1,2], 'index': [0, 0, 0, 1]},
        },
        {
            'in': {'token': ["ab", "", "A"]},
            'out': {'item': ["a", "b", None, "A"], 'index': [0, 1, 0, 0]},
        },

    ]
