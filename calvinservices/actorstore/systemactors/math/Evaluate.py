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

from calvin.actor.actor import Actor, manage, condition, calvinlib
from calvin.utilities.calvinlogger import get_actor_logger
from calvin.runtime.north.calvin_token import ExceptionToken


_log = get_actor_logger(__name__)


class Evaluate(Actor):
    """
    documentation:
    - Evaluate arithmetic expression 'expr' with two arguments, passed as (a string) argument.
    ports:
    - direction: in
      help: a number
      name: x
    - direction: in
      help: a number
      name: y
    - direction: out
      help: value expr with x and y substituted for given values
      name: result
    requires:
    - math.arithmetic.eval
    """
    @manage(['expr'])
    def init(self, expr):
        self.expr = expr if type(expr) is str or type(expr) is unicode else None
        self.setup()

    def setup(self):
        self.math = calvinlib.use('math.arithmetic.eval')

    def did_migrate(self):
        self.setup()


    @condition(['x', 'y'], ['result'])
    def compute(self, a, b):
        if self.expr:
            result = self.math.eval(self.expr, {'x':a, 'y':b})
        else :
            result = None
        if isinstance(result, basestring):
            result = ExceptionToken(result)
        return (result, )

    action_priority = ( compute, )
    


    test_args = ['x+y']
    test_set = [
        {
            'setup': [lambda self: self.init('x * y')],
            'inports': {'x': [1, 2, 3, 4], 'y':[1, 2, 3, 4]},
            'outports': {'result': [1, 4, 9, 16]},
        },
        {
            'setup': [lambda self: self.init('2*x + y + x * y')],
            'inports': {'x': [1, 2, 3, 4], 'y':[3, 3, 3, 3]},
            'outports': {'result': [8, 13, 18, 23]},
        },

    ]
