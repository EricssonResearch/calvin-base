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


_log = get_actor_logger(__name__)


class Compare(Actor):
    """
    documentation:
    - Perform a REL b where REL is a comparison relation passed as (a string) argument.
    - Allowed values for REL are =, <, >, <=, >=, !=
    ports:
    - direction: in
      help: a token
      name: a
    - direction: in
      help: a token
      name: b
    - direction: out
      help: true or false according to result of 'a' REL 'b'
      name: result
    requires:
    - math.arithmetic.eval
    """
    @manage(['rel'])
    def init(self, rel):
        self.rel = rel
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.math = calvinlib.use("math.arithmetic.eval")
        self.relation = self.math.relation(rel=self.rel)

    @condition(['a', 'b'], ['result'])
    def test(self, x, y):
        return (bool(self.relation(x, y)), )

    action_priority = ( test, )
    


    test_kwargs = {'rel': '='}
    test_set = [
        {
            'setup': [lambda self: self.init('=')],
            'inports': {'a': [1, 1, 0, 0], 'b':[1, 0, 1, 0]},
            'outports': {'result': [True, False, False, True]},
        },
        {
            'setup': [lambda self: self.init('!=')],
            'inports': {'a': [1, 1, 0, 0], 'b':[1, 0, 1, 0]},
            'outports': {'result': [False, True, True, False]},
        },

    ]
