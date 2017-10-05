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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

class LightBreaker(Actor):
    """
    React to changes in a sensor.

    Output:
      open : state true=closed, false=open
    """

    @manage(include=[])
    def init(self):
        self.setup()

    def setup(self):
        self.sensor = calvinsys.open(self, "io.lightbreaker")

    def will_migrate(self):
        calvinsys.close(self.sensor)
        self.sensor = None

    def will_end(self):
        if self.sensor:
            calvinsys.close(self.sensor)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: calvinsys.can_read(self.sensor))
    @condition([], ["open"])
    def state_change(self):
        value = calvinsys.read(self.sensor)
        return (True if value else False,)

    action_priority = (state_change, )
    requires = ['io.lightbreaker']


    test_calvinsys = {'io.lightbreaker': {'read': [True, False, True, False]}}
    test_set = [
        {
            'outports': {'open': [True, False, True, False]}
        }
    ]
