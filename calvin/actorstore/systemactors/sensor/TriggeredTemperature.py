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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class TriggeredTemperature(Actor):

    """
    Measure temperature.

    Inputs:
        trigger : any token triggers meausurement

    Outputs:
        centigrade :  temperature, in centigrade
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._temperature = calvinsys.open(self, "io.temperature")

    def teardown(self):
        if self._temperature:
            calvinsys.close(self._temperature)
        self._temperature = None

    def will_migrate(self):
        self.teardown()

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.teardown()

    @stateguard(lambda self: calvinsys.can_read(self._temperature))
    @condition([], ['centigrade'])
    def read_measurement(self):
        temperature = calvinsys.read(self._temperature)
        return (temperature,)

    @stateguard(lambda self: calvinsys.can_write(self._temperature))
    @condition(['trigger'], [])
    def start_measurement(self, _):
        calvinsys.write(self._temperature, True)


    action_priority = (read_measurement, start_measurement)
    requires =  ['io.temperature']


