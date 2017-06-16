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


class Light(Actor):

    """
    Set state of a light (e.g. an LED or a lightbulb)
    Input:
      on : true if light should be on, false if turned off
    """

    def init(self):
        self.light= None
        self.setup()

    def setup(self):
        self.light = calvinsys.open(self, "calvinsys.io.light")

    def will_migrate(self):
        calvinsys.close(self.light)
        self.light = None

    def will_end(self):
        if self.light :
            calvinsys.close(self.light)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self.light and calvinsys.can_write(self.light))
    @condition(action_input=("on",))
    def set_state(self, state):
        calvinsys.write(self.light, 1 if state else 0)

    action_priority = (set_state, )
    requires = ["calvinsys.io.light"]
