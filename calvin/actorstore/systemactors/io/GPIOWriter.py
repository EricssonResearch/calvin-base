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

from calvin.actor.actor import Actor, manage, condition


class GPIOWriter(Actor):

    """
    Set state of GPIO pin <pin>.
    Input:
      state : 1/0 for state high/low
    """

    @manage(["gpio_pin"])
    def init(self, gpio_pin):
        self.gpio_pin = gpio_pin
        self.setup()

    def setup(self):
        self.use("calvinsys.io.gpiohandler", shorthand="gpiohandler")
        self.gpio = self["gpiohandler"].open(self.gpio_pin, "o")

    def will_migrate(self):
        self.gpio.close()

    def will_end(self):
        self.gpio.close()

    def did_migrate(self):
        self.setup()

    @condition(action_input=("state",))
    def set_state(self, state):
        self.gpio.set_state(state)
        

    action_priority = (set_state, )
    requires = ["calvinsys.io.gpiohandler"]
