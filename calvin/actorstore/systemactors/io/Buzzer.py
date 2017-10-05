# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

from calvin.actor.actor import Actor, manage, condition, calvinsys, stateguard


class Buzzer(Actor):

    """
    Buzz
    Input:
      on : true/false for on/off
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self.buzzer = calvinsys.open(self, "io.buzzer")

    def will_end(self):
        if self.buzzer:
            calvinsys.close(self.buzzer)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda actor: calvinsys.can_write(actor.buzzer))
    @condition(["on"], [])
    def turn_on_off(self, on):
        calvinsys.write(self.buzzer, bool(on))

    action_priority = (turn_on_off, )
    requires = ["io.buzzer"]


    test_calvinsys = {'io.buzzer': {'write': [True, False, True, False]}}
    test_set = [
        {
            'inports': {'on': [True, False, True, False]},
        }
    ]
