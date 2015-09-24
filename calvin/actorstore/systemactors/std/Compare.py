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

import operator
from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_actor_logger


_log = get_actor_logger(__name__)


class Compare(Actor):
    """
    Perform a OP b where OP is the comparison operator passed as (a string) argument.

    Allowed values for OP are:
    =, <, >, <=, >=, !=

    Inputs:
      a : a token
      b : a token
    Outputs:
      result : true or false according to result of 'a' OP 'b'
    """
    @manage(['op'])
    def init(self, op):
        try:
            self.op = {
                '<': operator.lt,
                '<=': operator.le,
                '=': operator.eq,
                '!=': operator.ne,
                '>=': operator.ge,
                '>': operator.gt,
            }[op]
        except KeyError:
            _log.warning('Invalid operator %s, will always produce FALSE as result' % str(op))
            self.op = None

    @condition(['a', 'b'], ['result'])
    def test(self, a, b):
        res = bool(self.op(a, b)) if self.op else False
        return ActionResult(production=(res, ))


    action_priority = ( test, )

    test_args = ['=']

    test_set = [
        {
            'setup': [lambda self: self.init('=')],
            'in': {'a': [1, 1, 0, 0], 'b':[1, 0, 1, 0]},
            'out': {'result': [True, False, False, True]},
        },
        {
            'setup': [lambda self: self.init('!=')],
            'in': {'a': [1, 1, 0, 0], 'b':[1, 0, 1, 0]},
            'out': {'result': [False, True, True, False]},
        },

    ]

