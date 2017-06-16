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
    Measure distance. Takes the frequency of measurements, in Hz, as input.

    Outputs:
        meters : distance, in meters
    """

    @manage(['frequency'])
    def init(self, frequency):
        self.frequency = frequency
        self.setup()

    def setup(self):
        _log.info("setup")
        self._distance = calvinsys.open(self, "calvinsys.io.distance")
        self._timer = calvinsys.open(self, "calvinsys.sys.timer.repeating")
        calvinsys.write(self._timer, 1.0/self.frequency)

    def will_migrate(self):
        calvinsys.close(self._distance)
        calvinsys.close(self._timer)
        self._distance = None
        self._timer = None

    def did_migrate(self):
        self.setup()

    def will_end(self):
        if self._distance:
            calvinsys.close(self._distance)
        if self._timer :
            calvinsys.close(self._timer)

    @stateguard(lambda self: calvinsys.can_read(self._distance))
    @condition([], ['meters'])
    def read_measurement(self):
        distance = calvinsys.read(self._distance)
        return (distance/1000.0,)
        
    @stateguard(lambda self: calvinsys.can_read(self._timer) and calvinsys.can_write(self._distance))
    @condition([], [])
    def start_measurement(self):
        calvinsys.read(self._timer)
        calvinsys.write(self._distance, True)
    

    action_priority = (read_measurement, start_measurement)
    requires =  ['calvinsys.io.distance', 'calvinsys.sys.timer.repeating']


