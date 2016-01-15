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

    def exception_handler(self, action, args, context):
        exception = args[context['exceptions']['item'][0]]
        if self.n or type(exception) is not EOSToken:
            self._list = ExceptionToken()
        self.done = True
        return ActionResult()

    @manage(['n', '_list', 'done'])
    def init(self, n=1, pre_list=None, post_list=None):
        self.n = n if n > 0 else 0
        self._list = []
        self.pre_list = pre_list
        self.post_list = post_list
        self.done = False

    @condition(['item'], [])
    @guard(lambda self, item: not self.n and not self.done)
    def add_item_EOS(self, item):
        self._list.append(item)
        return ActionResult()

    @condition(['item'], [])
    @guard(lambda self, item: self.n and not self.done)
    def add_item(self, item):
        self._list.append(item)
        if len(self._list) == self.n:
            self.done = True
        return ActionResult()

    @condition([], ['list'])
    @guard(lambda self: self.done)
    def produce_list(self):
        if isinstance(self._list, list):
            res = (self.pre_list if self.pre_list else []) + self._list +(self.post_list if self.post_list else [])
        else:
            res = self._list
        self.done = False
        self._list = []
        return ActionResult(production=(res, ))

    action_priority = (produce_list, add_item, add_item_EOS)

    test_args = []
    test_kwargs = {}

    test_set = [
        {
            'in': {'item': [1, 2]},
            'out': {'list': [[1], [2]]},
        },
        {
            'setup': [lambda self: self.init(n=2)],
            'in': {'item': [1, 2]},
            'out': {'list': [[1, 2]]},
        },
        {
            'setup': [lambda self: self.init(n=2, pre_list=[5, 7])],
            'in': {'item': [1, 2]},
            'out': {'list': [[5, 7, 1, 2]]},
        },
        {
            'setup': [lambda self: self.init(n=2, post_list=[5, 7])],
            'in': {'item': [1, 2]},
            'out': {'list': [[1, 2, 5, 7]]},
        },
        {
            'setup': [lambda self: self.init(n=2, pre_list=[8, 9], post_list=[5, 7])],
            'in': {'item': [1, 2]},
            'out': {'list': [[8, 9, 1, 2, 5, 7]]},
        },
        {
            'setup': [lambda self: self.init(n=0)],
            'in': {'item': [1, 2, EOSToken()]},
            'out': {'list': [[1, 2]]},
        },
        # Error conditions
        {
            'setup': [lambda self: self.init(n=2)],
            'in': {'item': [1, EOSToken(), 3, 4]},
            'out': {'list': ['Exception', [3, 4]]},
        },
        {
            'setup': [lambda self: self.init(n=0)],
            'in': {'item': [1, ExceptionToken(), 3, EOSToken()]},
            'out': {'list': ['Exception', [3]]},
        },

    ]
