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
    Create a list

    Inputs:
      item: new value of item at index
    Outputs:
      list: JSON string rep of list.
    """


    @manage(['n', '_list', 'done'])
    def init(self, n=None):
        assert(n>0)
        self.n = n
        self._list = []
        self.done = False

    @condition(['item'], [])
    @guard(lambda self, item: not self.n and not self.done)
    def add_item_EOS(self, item):
        if isinstance(item, EOSToken):
            self.done = True
        else:
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
        res = self._list
        self.done = False
        self._list = []
        return ActionResult(production=(res, ))

    action_priority = (produce_list, add_item, add_item_EOS)
