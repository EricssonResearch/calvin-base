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

class GetValue(Actor):

    """
    Extract a value from a JSON dictionary formatted as a string

    FIXME: Should we produce an exception token in case of invalid JSON or no default?

    Inputs:
      dict: JSON dict formatted as a string
      key:  Key to look up
    Outputs:
      value: JSON string rep of value for the key or 'default' if missing key.
    """


    @manage(['default'])
    def init(self, default):
        self.default = default

    @condition(['dict', 'key'], ['value'])
    def get_value(self, d, key):
        keylist = key.split('.')
        try:
            res = d
            for key in keylist:
                res = res[key]
        except Exception as e:
            res = self.default
        return ActionResult(production=(res, ))

    action_priority = (get_value, )
