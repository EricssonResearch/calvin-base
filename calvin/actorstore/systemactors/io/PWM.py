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

from calvin.actor.actor import Actor, manage, condition, calvinsys


class PWM(Actor):

    """
    Pulse width modulation on runtime-defined pin.
    Input:
      dutycycle : new dutycycle
    """

    @manage(["dutycycle"])
    def init(self):
        self.dutycycle = None
        self.setup()

    def setup(self):
        self.pwm = calvinsys.open(self, "io.pwm")
        if self.dutycycle and calvinsys.can_write(self.pwm):
            calvinsys.write(self.pwm, self.dutycycle)

    def will_migrate(self):
        calvinsys.close(self.pwm)
        self.pwm = None

    def will_end(self):
        if self.pwm:
            calvinsys.close(self.pwm)

    def did_migrate(self):
        self.setup()

    @condition(["dutycycle"], [])
    def set_dutycycle(self, dutycycle):
        try:
            dc = int(dutycycle)
            if dc < 0: dc = 0
            if dc > 100: dc = 100
            self.dutycycle = dc
        except Exception:
            self.dutycycle = 0

        if calvinsys.can_write(self.pwm):
            calvinsys.write(self.pwm, self.dutycycle)

    action_priority = (set_dutycycle, )
    requires = ["io.pwm"]


    test_calvinsys = {'io.pwm': {'write': [1, 99, 0, 100]}}
    test_set = [
        {
            'inports': {'dutycycle': [1, 99, -1, 101]},
        }
    ]
