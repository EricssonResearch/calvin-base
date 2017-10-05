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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys


class Light(Actor):

    """
    Set state of a light (e.g. an LED or a lightbulb)
    Input:
      on : true if light should be on, false if turned off
    """

    @manage(include = ["light"])
    def init(self):
        self.light = calvinsys.open(self, "io.light")

    @stateguard(lambda self: calvinsys.can_write(self.light))
    @condition(action_input=("on",))
    def light(self, on):
        calvinsys.write(self.light, 1 if on else 0)

    action_priority = (light, )
    requires = ["io.light"]


    test_calvinsys = {'io.light': {'write': [1, 0, 1, 0]}}
    test_set = [
        {
            'inports': {'on': [True, False, True, False]},
        }
    ]
