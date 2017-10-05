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


class Knob(Actor):

    """
    Read a knob to see which way it turned.

    Outputs:
        direction: clockwise or anti-clockwise
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._knob = calvinsys.open(self, "io.knob")

    def will_migrate(self):
        calvinsys.close(self._knob)
        self._knob = None

    def will_end(self):
        if self._knob:
            calvinsys.close(self._knob)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: calvinsys.can_read(self._knob))
    @condition([], ["direction"])
    def trigger(self):
        return (calvinsys.read(self._knob),)

    action_priority = (trigger, )
    requires = ['io.knob']


    test_calvinsys = {'io.knob': {'read': [-1, 1, 0, 1]}}
    test_set = [
        {
            'outports': {'direction': [-1, 1, 0, 1]}
        }
    ]
