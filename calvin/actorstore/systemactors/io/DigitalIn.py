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


class DigitalIn(Actor):

    """
    Edge triggered digital input in runtime-defined pin.
    Outputs:
        state: 1/0 when edge goes high/low
    """

    @manage()
    def init(self):
        self._pin = None
        self.setup()

    def setup(self):
        self._pin = calvinsys.open(self, "io.digitalin")

    def will_migrate(self):
        if self._pin:
            calvinsys.close(self._pin)
        self._pin = None

    def will_end(self):
        if self._pin :
            calvinsys.close(self._pin)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self._pin and calvinsys.can_read(self._pin))
    @condition([], ["state"])
    def read_pin(self):
        state = calvinsys.read(self._pin)
        return (1 if state else 0,)

    action_priority = (read_pin, )
    requires = ["io.digitalin"]


    test_calvinsys = {'io.digitalin': {'read': [1,0,1,0]}}
    test_set = [
        {
            'outports': {'state': [1,0,1,0]}
        }
    ]
