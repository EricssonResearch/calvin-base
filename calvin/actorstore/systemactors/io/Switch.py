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

class Switch(Actor):
    """
    Creates a on/off switch.

    Output:
      state : true/false according to switch state
    """

    @manage([])
    def init(self):
        self.use("calvinsys.io.switch", shorthand="switch")

    def will_migrate(self):
        print "FIXME: migrate button"
        pass
        # self.button.destroy()

    @stateguard(lambda self: self["switch"] and self["switch"].has_data())
    @condition([], ["state"])
    def action(self):
        return (self["switch"].state(),)

    action_priority = (action, )
    requires = ['calvinsys.io.switch']


