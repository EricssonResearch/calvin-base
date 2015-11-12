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

from calvin.actor.actor import Actor, ActionResult, manage, condition


class GPIOPWM(Actor):

    """
    GPIO pulse width modulation on <pin>.
    Input:
      dutycycle : change dutycycle
      frequency : change frequency
    """

    @manage(["gpio_pin", "frequency", "dutycycle"])
    def init(self, gpio_pin, frequency, dutycycle):
        self.gpio_pin = gpio_pin
        self.frequency = frequency
        self.dutycycle = dutycycle
        self.setup()

    def setup(self):
        self.use("calvinsys.io.gpiohandler", shorthand="gpiohandler")
        self.gpio = self["gpiohandler"].open(self.gpio_pin, "o")
        self.gpio.pwm_start(self.frequency, self.dutycycle)

    def will_migrate(self):
        self.gpio.pwm_stop()
        self.gpio.close()

    def will_end(self):
        self.gpio.pwm_stop()
        self.gpio.close()

    def did_migrate(self):
        self.setup()

    @condition(action_input=("dutycycle",))
    def set_dutycycle(self, dutycycle):
        self.gpio.pwm_set_dutycycle(dutycycle)
        return ActionResult()

    @condition(action_input=("frequency",))
    def set_frequency(self, frequency):
        self.gpio.pwm_set_frequency(frequency)
        return ActionResult()

    action_priority = (set_dutycycle, set_frequency)
    requires = ["calvinsys.io.gpiohandler"]
