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
from copy import copy

class Items(Actor):

    """
    Extract all items from a JSON list

    FIXME: Should we produce an exception token in case of invalid JSON?

    Inputs:
      list:  a list
    Outputs:
      item: items of list in order
    """


    @manage(['data', 'has_data'])
    def init(self):
        self.data = []
        self.has_data = False

    @condition(['list'], [])
    @guard(lambda self, data: not self.has_data)
    def consume_list(self, data):
        try:
            self.data = copy(data)
            self.has_data = True
        except:
            pass
        return ActionResult()

    @condition([], ['item'])
    @guard(lambda self: self.has_data and len(self.data))
    def produce_item(self):
        res = self.data.pop(0)
        if not self.data:
            self.data = []
            self.has_data = False
        return ActionResult(production=(res, ))


    action_priority = (produce_item, consume_list)
