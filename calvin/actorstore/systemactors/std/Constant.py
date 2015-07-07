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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class Constant(Actor):
    """
    Send predetermined data on output.
    Outputs:
      token : Some data
    """
    @manage(['data', 'n', 'dump'])
    def init(self, data, n=1, dump=False):
        self.data = data
        self.n = n
        self.dump = dump

    def log(self, data):
        print "%s<%s>: %s" % (self.__class__.__name__, self.id, data)

    @condition([], ['token'])
    @guard(lambda self: self.n > 0 or self.n == -1)
    def send_it(self):
        if self.n > 0:
            self.n -= 1
        if self.dump:
            self.log(self.data)
        return ActionResult(production=(self.data,))

    action_priority = (send_it, )

    test_args = (42,)
    test_kwargs = {"n": 3}

    test_set = [
        {
            'in': {},
            'out': {'token': [42]}
        } for i in range(3)
    ]

    test_set += [
        {
            'in': {},
            'out': {'token': []}
        }
    ]
