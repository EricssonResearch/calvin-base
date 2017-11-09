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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class Distance(Actor):

    """
    Measure distance. Takes the period of measurements, in seconds, as input.

    Outputs:
        meters : distance, in meters
    """

    @manage(['period', 'distance', 'timer'])
    def init(self, period):
        self.period = period
        self.distance = calvinsys.open(self, "io.distance")
        self.timer = calvinsys.open(self, "sys.timer.repeating", period=period)

    @stateguard(lambda self: calvinsys.can_read(self.distance))
    @condition([], ['meters'])
    def read_measurement(self):
        value = calvinsys.read(self.distance)
        return (value,)

    @stateguard(lambda self: calvinsys.can_read(self.timer) and calvinsys.can_write(self.distance))
    @condition([], [])
    def start_measurement(self):
        calvinsys.read(self.timer)
        calvinsys.write(self.distance, True)

    action_priority = (read_measurement, start_measurement)
    requires = ['io.distance', 'sys.timer.repeating']


    test_kwargs = {'period': 10}
    test_calvinsys = {'io.distance': {'read': [10, 12, 0, 5],
                                      'write': [True]},
                      'sys.timer.repeating': {'read': ['dummy'],
                                              'write': [10]}}
    test_set = [
        {
            'outports': {'meters': [10, 12, 0, 5]}
        }
    ]
