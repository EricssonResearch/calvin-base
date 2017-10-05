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

from calvin.actor.actor import Actor, condition, stateguard, manage, calvinsys
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)

class ServoMotor(Actor):

    """
    Rotate servo given degrees.
    Input:
      angle : set servo to given angle
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._servo = calvinsys.open(self, "io.servomotor")
        calvinsys.write(self._servo, 90)

    @stateguard(lambda self: calvinsys.can_write(self._servo))
    @condition(action_input=("angle",))
    def set_angle(self, angle):
        calvinsys.write(self._servo, angle)

    action_priority = (set_angle, )
    requires = ["io.servomotor"]


    test_calvinsys = {'io.servomotor': {'write': [90, -90, 90, 180, -45]}}
    test_set = [
        {
            'inports': {'angle': [-90, 90, 180, -45]},
        }
    ]
