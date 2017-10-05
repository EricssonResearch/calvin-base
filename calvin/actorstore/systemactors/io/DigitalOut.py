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


class DigitalOut(Actor):

    """
    Set runtime defined-pin to inport state.
    Inputs:
        state: 1/0
    """

    @manage()
    def init(self):
        self._pin = None
        self.setup()

    def setup(self):
        self._pin = calvinsys.open(self, "io.digitalout")

    def will_migrate(self):
        if self._pin:
            calvinsys.close(self._pin)
        self._pin = None

    def will_end(self):
        if self._pin :
            calvinsys.close(self._pin)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self._pin and calvinsys.can_write(self._pin))
    @condition(["state"], [])
    def write_pin(self, state):
        calvinsys.write(self._pin, 1 if state else 0)

    action_priority = (write_pin, )
    requires = ["io.digitalout"]


    test_calvinsys = {'io.digitalout': {'write': [1, 0, 1, 0]}}
    test_set = [
        {
            'inports': {'state': [1, 0, 1, 0]},
        }
    ]
