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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib

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
        self.setup()

    def setup(self):
        self.copy = calvinlib.use("copy")


    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: not self.has_data)
    @condition(['token'], [])
    def consume(self, data):
        if not data:
            # Empty list => null output
            self.data = None
        else:
            mutable = bool(type(data) is list or type(data) is dict)
            self.data = self.copy.copy(data) if mutable else data
        self.has_data = True
        self.index = 0


    @stateguard(lambda self: self.has_data and type(self.data) is list)
    @condition([], ['item', 'index'])
    def produce_listitem(self):
        res = self.data.pop(0)
        i = self.index
        self.index += 1
        if not self.data:
            self.data = None
            self.has_data = False
        return (res, i)

    @stateguard(lambda self: self.has_data and type(self.data) is dict)
    @condition([], ['item', 'index'])
    def produce_dictitem(self):
        k, v = self.data.popitem()
        if not self.data:
            self.data = None
            self.has_data = False
        return (v, k)

    @stateguard(lambda self: self.has_data and isinstance(self.data, basestring))
    @condition([], ['item', 'index'])
    def produce_stringitem(self):
        res = self.data[0]
        self.data = self.data[1:]
        i = self.index
        self.index += 1
        if not self.data:
            self.data = None
            self.has_data = False
        return (res, i)

    @stateguard(lambda self: self.has_data)
    @condition([], ['item', 'index'])
    def produce_plainitem(self):
        res = self.data
        self.data = None
        self.has_data = False
        return (res, 0)

    action_priority = (produce_listitem, produce_dictitem, produce_stringitem, produce_plainitem, consume)
    requires = ['copy']


    test_args = []
    test_kwargs = {}
    test_set = [
        {
            'inports': {'token': [[1,2,3]]},
            'outports': {'item': [1,2,3], 'index': [0, 1, 2]},
        },
        {
            'inports': {'token': ["abcd"]},
            'outports': {'item': ["a", "b", "c", "d"], 'index': [0, 1, 2, 3]},
        },
        {
            'inports': {'token': [1,2,3]},
            'outports': {'item': [1, 2, 3], 'index': [0, 0, 0]},
        },
        {
            'inports': {'token': {"a":"A", "b":1}},
            'outports': {'item': set([1, "A"]), 'index': set(["a", "b"])},
        },
        {
            'inports': {'token': [""]},
            'outports': {'item': [None], 'index': [0]},
        },
        {
            'inports': {'token': [{}]},
            'outports': {'item': [None], 'index': [0]},
        },
        {
            'inports': {'token': [[]]},
            'outports': {'item': [None], 'index': [0]},
        },
        {
            'inports': {'token': [[], []]},
            'outports': {'item': [None, None], 'index': [0, 0]},
        },

        {
            'inports': {'token': [[1], [2]]},
            'outports': {'item': [1, 2], 'index': [0, 0]},
        },
        {
            'inports': {'token': [[], [1,2,3]]},
            'outports': {'item': [None, 1,2,3], 'index': [0, 0, 1, 2]},
        },
        {
            'inports': {'token': [[], [], [1,2]]},
            'outports': {'item': [None, None, 1,2], 'index': [0, 0, 0, 1]},
        },
        {
            'inports': {'token': ["ab", "", "A"]},
            'outports': {'item': ["a", "b", None, "A"], 'index': [0, 1, 0, 0]},
        },

    ]
