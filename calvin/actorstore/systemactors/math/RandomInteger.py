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

from calvin.utilities.calvinlogger import get_actor_logger
from calvin.actor.actor import Actor, manage, condition, calvinlib

_log = get_actor_logger(__name__)


class RandomInteger(Actor):
    """
    Produce random integer in range [lower ... upper-1]

    Inputs:
      trigger : Any token
    Outputs:
      integer : Random integer in range [lower ... upper-1]
    """

    @manage(['lower', 'upper'])
    def init(self, lower, upper):
        self.lower = lower
        self.upper = upper

        self.setup()

    def setup(self):
        self.rng = calvinlib.use("math.random")

    def did_migrate(self):
        self.setup()

    @condition(action_input=['trigger'], action_output=['integer'])
    def action(self, trigger):
        return self.rng.random_integer(lower=self.lower, upper=self.upper),

    action_priority = (action, )
    requires = ['math.random']


    test_kwargs = {'lower': 1, 'upper': 2}
    test_set = [
        {
            'inports': {'trigger': [True, 1, "a"]},
            'outports': {'integer': [1, 1, 1]}
        }
    ]
