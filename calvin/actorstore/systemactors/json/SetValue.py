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
from copy import deepcopy

class SetValue(Actor):

    """
    Modify a container (list or dictionary)

    If container is a list then the key must be an integer index (zero-based), or a list of indices if for nested lists.
    If container is a dictionary the key must be a string or list of (string) keys for nested dictionaries.
    It is OK to make a key list of mixed strings and integers if the container comprises nested dictionaries and lists.
    Produce an ExceptionToken if mapping between key and (sub-)container is incorrect, or if a  integer index is out of range.
    N.B. This actor will incur a performance penalty from a deep copy operation. Use wisely.

    Inputs:
      container: a list or dictionary
      key: index (integer), key (string), or a (possibly mixed) list for nested containers
      value: value to set
    Outputs:
      container:  a modified container
    """

    def exception_handler(self, action, args, context):
        return ActionResult(production=(ExceptionToken(),))

    @manage()
    def init(self):
        pass

    def _type_mismatch(self, container, key):
        t_cont = type(container)
        t_key = type(key)
        return (t_cont is list and t_key is not int) or (t_cont is dict and not isinstance(key, basestring))


    @condition(['container', 'key', 'value'], ['container'])
    def set_value(self, data, key, value):
        keylist = key if type(key) is list else [key]
        container = deepcopy(data)
        try:
            res = container
            for key in keylist[:-1]:
                if self._type_mismatch(res, key):
                    raise Exception()
                res = res[key]
            if self._type_mismatch(res, keylist[-1]):
                raise Exception()
            res[keylist[-1]] = value
        except:
            container = ExceptionToken()
        return ActionResult(production=(container, ))

    action_priority = (set_value, )

    test_args = []
    test_kwargs = {}

    test_set = [
        {
            'in': {'container': [{'a':1}], 'key':['a'], 'value':[42]},
            'out': {'container': [{'a':42}]},
        },
        {
            'in': {'container': [[1,2,3]], 'key':[1], 'value':[42]},
            'out': {'container': [[1,42,3]]},
        },
        {
            'in': {'container': [[1,{'a':2},3]], 'key':[[1, 'a']], 'value':[42]},
            'out': {'container': [[1,{'a':42},3]]},
        },
        {
            'in': {'container': [{'a':[1, 2, 3]}], 'key':[['a', 1]], 'value':[42]},
            'out': {'container': [{'a':[1, 42, 3]}]},
        },
        # Error conditions
        {
            'in': {'container': [[1,2,3]], 'key':['a'], 'value':[42]},
            'out': {'container': ['Exception']},
        },
        {
            'in': {'container': [{'a':1}], 'key':[1], 'value':[42]},
            'out': {'container': ['Exception']},
        },
        {
            'in': {'container': [[1,{'a':2},3]], 'key':[[1, 2]], 'value':[42]},
            'out': {'container': ['Exception']},
        },

    ]
