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

class Dict(Actor):

    """
    Create a dict

    Inputs:
      key:
      value:
    Outputs:
      dict:
    """


    @manage(['n', '_dict', 'done'])
    def init(self, n=None):
        assert(n>0)
        self.n = n
        self._dict = {}
        self.done = False

    @condition(['key', 'value'], [])
    @guard(lambda self, key, value: not self.n and not self.done)
    def add_entry_EOS(self, item):
        if isinstance(key, EOSToken) and isinstance(value, EOSToken):
            self.done = True
        elif isinstance(key, EOSToken) or isinstance(value, EOSToken):
            raise Exception("Bad key/value pair (%s/%s)" % (key, value))
        else:
            self._dict[key]=value
        return ActionResult()


    @condition(['key', 'value'], [])
    @guard(lambda self, key, value: self.n and not self.done)
    def add_entry(self, key, value):
        self._dict[key]=value
        if len(self._dict) == self.n:
            self.done = True
        return ActionResult()

    @condition([], ['dict'])
    @guard(lambda self: self.done)
    def produce_dict(self):
        res = self._dict
        self.done = False
        self._dict = {}
        return ActionResult(production=(res, ))

    action_priority = (produce_dict, add_entry, add_entry_EOS)
