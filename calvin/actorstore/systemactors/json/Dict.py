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

    Consume 'n' key/value pairs to produce a dictionary, 'n' defaults to 1.
    If 'n' is zero or negative, consume key/value pairs until EOS encountered
    on both input ports. If EOS is only encountered on one port, produce an execption.

    Inputs:
      key: key must be string
      value: can be any token
    Outputs:
      dict: dictionary or Exception
    """


    @manage(['n', '_dict', 'done'])
    def init(self, n=1):
        self.n = n if n > 0 else 0
        self._dict = {}
        self.done = False

    def _bail(self):
        self._dict = ExceptionToken()
        self.done = True

    def exception_handler(self, action, args, context):
        if self.n or not ('key' in context['exceptions'] and 'value' in context['exceptions']):
            self._bail()
        self.done = True
        return ActionResult()

    @condition(['key', 'value'], [])
    @guard(lambda self, key, value: not self.n and not self.done)
    def add_entry_EOS(self, key, value):
        if isinstance(key, basestring):
            self._dict[key] = value
        else:
            self._bail()
        return ActionResult()

    @condition(['key', 'value'], [])
    @guard(lambda self, key, value: self.n and not self.done)
    def add_entry(self, key, value):
        if isinstance(key, basestring):
            self._dict[key]=value
            self.done = bool(len(self._dict) == self.n)
        else:
            self._bail()
        return ActionResult()

    @condition([], ['dict'])
    @guard(lambda self: self.done)
    def produce_dict(self):
        res = self._dict
        self.done = False
        self._dict = {}
        return ActionResult(production=(res, ))

    action_priority = (produce_dict, add_entry, add_entry_EOS)


    test_set = [
        {
            'in': {'key': ["a", "b"], 'value': [1, 2]},
            'out': {'dict': [{"a":1}, {"b":2}]},
        },
        {
            'setup':[lambda self: self.init(n=2)],
            'in': {'key': ["a", "b"], 'value': [1, 2]},
            'out': {'dict': [{"a":1, "b":2}]},
        },
        {
            'setup':[lambda self: self.init(n=0)],
            'in': {'key': ["a", "b", EOSToken()], 'value': [1, 2, EOSToken()]},
            'out': {'dict': [{"a":1, "b":2}]},
        },
        # Error conditions
        {
            'setup':[lambda self: self.init(n=0)],
            'in': {'key': ["a", EOSToken()], 'value': [1, 2]},
            'out': {'dict': ['Exception']},
        },
        {
            'setup':[lambda self: self.init(n=2)],
            'in': {'key': ["a", 1, "b", "c"], 'value': [10, 20, 30, 40]},
            'out': {'dict': ['Exception', {"b":30, "c":40}]},
        },

    ]
