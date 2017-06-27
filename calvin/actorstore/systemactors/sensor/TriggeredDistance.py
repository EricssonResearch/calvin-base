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

class TriggeredDistance(Actor):

    """
    Measure distance.

    Inputs:
        trigger : any token triggers meausurement

    Outputs:
        meters : distance, in meters
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._distance = calvinsys.open(self, "calvinsys.io.distance")

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
    def start_measurement(self, _):
        calvinsys.write(self._distance, True)


    action_priority = (read_measurement, start_measurement)
    requires =  ['calvinsys.io.distance']


