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

from calvin.actor.actor import Actor, condition, stateguard, calvinsys


class Led(Actor):

    """
    Set state of a LED (Light Emitting Diode)
    Input:
      state : 1/0 for on/off
    """

    def init(self):
        self.led = None
        self.setup()

    def setup(self):
        self.led = calvinsys.open(self, "calvinsys.io.led")

    def will_migrate(self):
        calvinsys.close(self.led)

    def will_end(self):
        calvinsys.close(self.led)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self.led and calvinsys.can_write(self.led))
    @condition(action_input=("state",))
    def set_state(self, state):
        calvinsys.write(self.led, state)

    action_priority = (set_state, )
    requires = ["calvinsys.io.led"]
