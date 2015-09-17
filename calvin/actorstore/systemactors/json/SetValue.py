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

class SetValue(Actor):

    """
    Set/modify a value in a JSON dictionary

    FIXME: Should we produce an exception token in case of invalid JSON or no default?

    Inputs:
      dict:  a dict
      key:   Key
      value: Value
    Outputs:
      dict:  modified dict
    """


    @manage()
    def init(self):
        pass

    @condition(['dict', 'key', 'value'], ['dict'])
    def set_value(self, data, key, value):
        keylist = key.split('.')
        try:
            tmp = data
            for key in keylist[0:-1]:
                tmp = tmp[key]
            tmp[keylist[-1]] = value
        except Exception as e:
            pass
        return ActionResult(production=(data, ))

    action_priority = (set_value, )
