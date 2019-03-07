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
from calvin.common.calvinlogger import get_logger

_log = get_logger(__name__)

class TriggeredDistance(Actor):

    """
    documentation:
    - Measure distance.
    ports:
    - direction: in
      help: any token triggers meausurement
      name: trigger
    - direction: out
      help: distance, in meters
      name: meters
    requires:
    - io.distance
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._distance = calvinsys.open(self, "io.distance")

    def teardown(self):
        if self._distance:
            calvinsys.close(self._distance)
        self._distance = None

    def will_migrate(self):
        self.teardown()

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.teardown()

    @stateguard(lambda self: calvinsys.can_read(self._distance))
    @condition([], ['meters'])
    def read_measurement(self):
        distance = calvinsys.read(self._distance)
        return (distance,)

    @stateguard(lambda self: calvinsys.can_write(self._distance))
    @condition(['trigger'], [])
    def trigger_measurement(self, _):
        calvinsys.write(self._distance, True)

    action_priority = (read_measurement, trigger_measurement)
    


    test_calvinsys = {'io.distance': {'read': [10, 12, 0, 5],
                                      'write': [True]}}
    test_set = [
        {
            'inports': {'trigger': [True]},
            'outports': {'meters': [10, 12, 0, 5]}
        }
    ]
