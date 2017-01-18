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
from calvin.actor.actor import Actor, ActionResult, manage, condition

_log = get_actor_logger(__name__)


class Random(Actor):
    """
    Produce random integer in range [minimum ... maximum]

    Inputs:
      trigger : Any token
    Outputs:
      integer : Random integer in range [minimum ... maximum]
    """

    @manage(['min', 'max'])
    def init(self, minimum, maximum):
        self.min = minimum
        self.max = maximum

        self.setup()

    def setup(self):
        self.use('calvinsys.native.python-random', shorthand="random")

    def did_migrate(self):
        self.setup()

    @condition(action_input=['trigger'], action_output=['integer'])
    def action(self, trigger):
        result = self['random'].randint(self.min, self.max)
        return (result, )

    action_priority = (action, )

    requires = ['calvinsys.native.python-random']
