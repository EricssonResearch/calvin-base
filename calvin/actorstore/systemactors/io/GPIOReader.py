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

from calvin.actor.actor import Actor, manage, condition, stateguard


class GPIOReader(Actor):

    """
    Edge triggered GPIO state reader for pin <pin>

    Outputs:
      state: 0/1 when low/high edge detected
    """

    @manage(['gpio_pin', 'edge', 'pull'])
    def init(self, gpio_pin, edge, pull):
        self.gpio_pin = gpio_pin
        self.edge = edge
        self.pull = pull
        self.gpio = None
        self.setup()

    def setup(self):
        self.use("calvinsys.io.gpiohandler", shorthand="gpiohandler")
        self.gpio = self["gpiohandler"].open(self.gpio_pin, "i", self.pull)
        self.gpio.detect_edge(self.edge)

    def will_migrate(self):
        self.gpio.close()

    def will_end(self):
        self.gpio.close()

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self.gpio is not None and self.gpio.edge_detected())
    @condition(action_output=('state',))
    def get_state(self):
        return (self.gpio.edge_value(), )

    action_priority = (get_state, )
    requires = ['calvinsys.io.gpiohandler']
