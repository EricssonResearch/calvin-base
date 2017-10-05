# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.actor.actor import Actor, manage, condition
from calvin.runtime.north.calvin_token import ExceptionToken
from copy import deepcopy

class SetDefault(Actor):

    """
    Modify a dictionary part of container if key does not exist (key must be string)

    If container is a list then the key must be an integer index (zero-based), or a list of indices if for nested lists.
    If container is a dictionary the key must be a string or list of (string) keys for nested dictionaries.
    It is OK to make a key list of mixed strings and integers if the container comprises nested dictionaries and lists.
    Produce an ExceptionToken if mapping between key and (sub-)container is incorrect, or if a  integer index is out of range.
    N.B. This actor will incur a performance penalty from a deep copy operation. Use wisely.

    Inputs:
      container: a list or dictionary
      key: key (string), or a (possibly mixed) list for nested containers
      value: default value to set
    Outputs:
      container:  a modified container
    """

    def exception_handler(self, action, args):
        return (ExceptionToken(),)

    @manage()
    def init(self):
        pass

    def _check_type_mismatch(self, container, key):
        t_cont = type(container)
        t_key = type(key)
        mismatch = (t_cont is list and t_key is not int) or (t_cont is dict and not isinstance(key, basestring))
        if mismatch:
            raise Exception()

    def _set_default(self, container, key, value):
        keylist = key if type(key) is list else [key]
        try:
            res = container
            for key in keylist[:-1]:
                self._check_type_mismatch(res, key)
                res = res[key]
            self._check_type_mismatch(res, keylist[-1])
            if not res.has_key(keylist[-1]):
                res[keylist[-1]] = value
        except:
            container = ExceptionToken()
        return container

    @condition(['container', 'key', 'value'], ['container'])
    def set_default(self, data, key, value):
        container = self._set_default(deepcopy(data), key, value)
        return (container, )

    action_priority = (set_default, )

    test_args = []
    test_kwargs = {}

    test_set = [
        {
            'inports': {'container': [{'a':1}], 'key':['a'], 'value':[42]},
            'outports': {'container': [{'a':1}]},
        },
        {
            'inports': {'container': [{'a':2}], 'key':['c'], 'value':[42]},
            'outports': {'container': [{'a':2, 'c': 42}]},
        },
        {
            'inports': {'container': [[1,{'a':3},3]], 'key':[[1, 'a']], 'value':[42]},
            'outports': {'container': [[1,{'a':3},3]]},
        },
        {
            'inports': {'container': [[1,{'c':4},3]], 'key':[[1, 'a']], 'value':[42]},
            'outports': {'container': [[1,{'a': 42, 'c':4},3]]},
        },
        # Error conditions
        {
            'inports': {'container': [[1,2,3]], 'key':[1], 'value':[42]},
            'outports': {'container': ['Exception']},
        },
        {
            'inports': {'container': [{'a':5}], 'key':[1], 'value':[42]},
            'outports': {'container': ['Exception']},
        },
        {
            'inports': {'container': [{'a':6}], 'key':[1], 'value':[42]},
            'outports': {'container': ['Exception']},
        }
    ]
