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

class SetItem(Actor):

    """
    Set item in list

    FIXME: Exception for invalid index

    Inputs:
      list:  a list
      index: Index of item (zero-based)
      value: new value of item at index
    Outputs:
      list:  a modified list
    """


    @manage()
    def init(self):
        pass

    @condition(['list', 'index', 'value'], ['list'])
    def set_item(self, data, index, value):
        try:
            data[index] = value
        except:
            data
            return ActionResult(did_fire=False)
        return ActionResult(production=(data, ))

    action_priority = (set_item, )
