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

class Temperature(Actor):

    """
    Measure temperature. Takes the period of measurements, in seconds, as input.

    Outputs:
        centigrade :  temperature, in centigrade
    """

    @manage(['period', 'timer', 'temperature'])
    def init(self, period):
        self.period = period
        self.temperature = calvinsys.open(self, "io.temperature")
        self.timer = calvinsys.open(self, "sys.timer.once", period=period)

    @stateguard(lambda self: calvinsys.can_read(self.temperature) and calvinsys.can_write(self.timer))
    @condition([], ['centigrade'])
    def read_measurement(self):
        value = calvinsys.read(self.temperature)
        # reset timer
        calvinsys.write(self.timer, self.period)
        return (value,)

    @stateguard(lambda self: calvinsys.can_read(self.timer) and calvinsys.can_write(self.temperature))
    @condition([], [])
    def start_measurement(self):
        # ack timer
        calvinsys.read(self.timer)
        # start measurement
        calvinsys.write(self.temperature, True)

    action_priority = (read_measurement, start_measurement)
    requires = ['io.temperature', 'sys.timer.once']


    test_kwargs = {'period': 10}
    test_calvinsys = {'io.temperature': {'read': [10, 12, 0, 5],
                                         'write': [True]},
                      'sys.timer.once': {'read': ['dummy'],
                                         'write': [10, 10, 10, 10]}}
    test_set = [
        {
            'outports': {'centigrade': [10, 12, 0, 5]}
        }
    ]
