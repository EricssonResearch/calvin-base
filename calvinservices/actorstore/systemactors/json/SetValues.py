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

from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken
from copy import deepcopy

class SetValues(Actor):

    """
    documentation:
    - Modify a container (list or dictionary)
    - If container is a list then the key must be an integer index (zero-based), or a
      list of indices if for nested lists. If container is a dictionary the key must be
      a string or list of (string) keys for nested dictionaries. It is OK to make a key
      list of mixed strings and integers if the container comprises nested dictionaries
      and lists. Produce an ExceptionToken if mapping between key and (sub-)container
      is incorrect, or if a integer index is out of range. N.B. This actor will incur
      a performance penalty from a deep copy operation. Use wisely.
    ports:
    - direction: in
      help: a list or dictionary
      name: container
    - direction: in
      help: A list of indices (integer), keys (string), or a (possibly mixed) list for
        nested containers
      name: keys
    - direction: in
      help: A list of values to set for the corresponding keys
      name: values
    - direction: out
      help: a modified container
      name: container
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

    def _set_value(self, container, key, value):
        keylist = key if type(key) is list else [key]
        try:
            res = container
            for key in keylist[:-1]:
                self._check_type_mismatch(res, key)
                res = res[key]
            self._check_type_mismatch(res, keylist[-1])
            res[keylist[-1]] = value
        except:
            container = ExceptionToken()
        return container


    @condition(['container', 'keys', 'values'], ['container'])
    def set_values(self, data, keys, values):
        container = deepcopy(data)
        for key, value in zip(keys, values):
            if type(container) is ExceptionToken:
                break
            container = self._set_value(container, key, value)
        return (container, )

    action_priority = (set_values, )

    
    test_kwargs = {}

    test_set = [
        {
            'inports': {'container': [{'a':1}], 'keys':[['a']], 'values':[[42]]},
            'outports': {'container': [{'a':42}]},
        },
        {
            'inports': {'container': [[1,2,3]], 'keys':[[1]], 'values':[[42]]},
            'outports': {'container': [[1,42,3]]},
        },
        {
            'inports': {'container': [[1,{'a':2},3]], 'keys':[[[1, 'a'], 2]], 'values':[[42, 43]]},
            'outports': {'container': [[1,{'a':42},43]]},
        },
        {
            'inports': {'container': [{'a':[1, 2, 3]}], 'keys':[[['a', 1]]], 'values':[[42]]},
            'outports': {'container': [{'a':[1, 42, 3]}]},
        },
        # # Error conditions
        {
            'inports': {'container': [[1,2,3]], 'keys':[['a']], 'values':[[42]]},
            'outports': {'container': ['Exception']},
        },
        {
            'inports': {'container': [{'a':1}], 'keys':[[1]], 'values':[[42]]},
            'outports': {'container': ['Exception']},
        },
        {
            'inports': {'container': [[1,{'a':2},3]], 'keys':[[0, [1, 2]]], 'values':[[42, 43]]},
            'outports': {'container': ['Exception']},
        },

    ]
