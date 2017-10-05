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

class Switch(Actor):
    """
    Creates a on/off switch.

    Output:
      state : 0/1 according to switch state
    """

    @manage([])
    def init(self):
        self.switch = None
        self.setup()

    def setup(self):
        self.switch = calvinsys.open(self, "io.switch")

    def will_migrate(self):
        calvinsys.close(self.switch)

    def did_migrate(self):
        self.setup()

    def will_end(self):
        calvinsys.close(self.switch)

    @stateguard(lambda self: self.switch and calvinsys.can_read(self.switch))
    @condition([], ["state"])
    def action(self):
        state = calvinsys.read(self.switch)
        return (state,)

    action_priority = (action, )
    requires = ['io.switch']


    test_calvinsys = {'io.switch': {'read': [1,0,1,0]}}
    test_set = [
        {
            'outports': {'state': [1,0,1,0]}
        }
    ]
