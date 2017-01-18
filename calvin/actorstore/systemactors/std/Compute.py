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
from calvin.actor.actor import Actor, manage, condition
from calvin.utilities.calvinlogger import get_actor_logger


_log = get_actor_logger(__name__)


class Compute(Actor):
    """
    Perform a OP b where OP is the operator passed as (a string) argument.

    Allowed values for OP are:
    +, -, *, /, div (integer division), mod (modulo)

    Inputs:
      a : a token
      b : a token
    Outputs:
      result : result of 'a' OP 'b'
    """
    @manage(['op_string'])
    def init(self, op):
        self.op_string = op
        self.setup()
        
    def setup(self):
        try:
            self.op = {
                '+': operator.add,
                '-': operator.sub,
                '*': operator.mul,
                '/': operator.div,
                'div': operator.floordiv,
                'mod': operator.mod,
            }[self.op_string]
        except KeyError:
            _log.warning('Invalid operator %s, will always produce NULL as result' % str(self.op_string))
            self.op = None
        
    def did_migrate(self):
        self.setup()
        
    @condition(['a', 'b'], ['result'])
    def compute(self, a, b):
        res = self.op(a, b) if self.op else None
        return (res, )


    action_priority = ( compute, )

    test_args = ['+']

    test_set = [
        {
            'setup': [lambda self: self.init('*')],
            'in': {'a': [1, 2, 3, 4], 'b':[1, 2, 3, 4]},
            'out': {'result': [1, 4, 9, 16]},
        },
        {
            'setup': [lambda self: self.init('mod')],
            'in': {'a': [1, 2, 3, 4], 'b':[3, 3, 3, 3]},
            'out': {'result': [1, 2, 0, 1]},
        },

    ]

