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

from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken

class List(Actor):

    """
    Create a list.

    Consumes 'n' tokens  to produce a list, 'n' defaults to 1. If 'n' is zero or negative,
    consumes tokens until EOS encountered (variable list length).
    The optional arguments pre_list and post_list are used to prepend and extend the list before
    delivering the final list.
    Will produce an ExceptionToken if EOS is encountered when n > 0, or if an ExceptionToken is
    encountered regardless of value of 'n'.

    Inputs:
      item: items to append to list
    Outputs:
      list: a list of consumed items
    """

    def exception_handler(self, action, args):
        if self.n or type(args[0]) is not EOSToken:
            self._list = ExceptionToken()
        self.done = True


    @manage(['n', '_list', 'done'])
    def init(self, n=1, pre_list=None, post_list=None):
        self.n = n if n > 0 else 0
        self._list = []
        self.pre_list = pre_list
        self.post_list = post_list
        self.done = False

    @stateguard(lambda self: not self.n and not self.done)
    @condition(['item'], [])
    def add_item_EOS(self, item):
        self._list.append(item)


    @stateguard(lambda self: self.n and not self.done)
    @condition(['item'], [])
    def add_item(self, item):
        self._list.append(item)
        if len(self._list) == self.n:
            self.done = True


    @stateguard(lambda self: self.done)
    @condition([], ['list'])
    def produce_list(self):
        if isinstance(self._list, list):
            res = (self.pre_list if self.pre_list else []) + self._list +(self.post_list if self.post_list else [])
        else:
            res = self._list
        self.done = False
        self._list = []
        return (res, )

    action_priority = (produce_list, add_item, add_item_EOS)

    test_args = []
    test_kwargs = {}

    test_set = [
        {
            'inports': {'item': [1, 2]},
            'outports': {'list': [[1], [2]]},
        },
        {
            'setup': [lambda self: self.init(n=2)],
            'inports': {'item': [1, 2]},
            'outports': {'list': [[1, 2]]},
        },
        {
            'setup': [lambda self: self.init(n=2, pre_list=[5, 7])],
            'inports': {'item': [1, 2]},
            'outports': {'list': [[5, 7, 1, 2]]},
        },
        {
            'setup': [lambda self: self.init(n=2, post_list=[5, 7])],
            'inports': {'item': [1, 2]},
            'outports': {'list': [[1, 2, 5, 7]]},
        },
        {
            'setup': [lambda self: self.init(n=2, pre_list=[8, 9], post_list=[5, 7])],
            'inports': {'item': [1, 2]},
            'outports': {'list': [[8, 9, 1, 2, 5, 7]]},
        },
        {
            'setup': [lambda self: self.init(n=0)],
            'inports': {'item': [1, 2, EOSToken()]},
            'outports': {'list': [[1, 2]]},
        },
        # Error conditions
        {
            'setup': [lambda self: self.init(n=2)],
            'inports': {'item': [1, EOSToken(), 3, 4]},
            'outports': {'list': ['Exception', [3, 4]]},
        },
        {
            'setup': [lambda self: self.init(n=0)],
            'inports': {'item': [1, ExceptionToken(), 3, EOSToken()]},
            'outports': {'list': ['Exception', [3]]},
        },

    ]
