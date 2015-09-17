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

class GetItem(Actor):

    """
    Extract a value from a JSON formatted string

    FIXME: Should we produce an exception token in case of invalid JSON or no default?

    Inputs:
      list:  JSON list
      index: Index of item (zero-based)
    Outputs:
      value: item at index or 'default' if invalid index, not a list, or invalid JSON.
    """


    @manage(['default'])
    def init(self, default):
        self.default = default

    @condition(['list', 'index'], ['value'])
    def get_item(self, data, index):
        try:
            res = data[index]
        except:
            res = self.default
        return ActionResult(production=(res, ))

    action_priority = (get_item, )
