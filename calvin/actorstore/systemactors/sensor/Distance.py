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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class Distance(Actor):

    """
        Measure distance. Takes the frequency of measurements, in Hz, as input.
        
    Outputs:
        meters : Measured distance, in meters
    """

    @manage(['frequency'])
    def init(self, frequency):
        self.frequency = frequency
        self.setup()

    def setup(self):
        self.use("calvinsys.sensors.distance", shorthand="distance")
        self['distance'].start(self.frequency)
        
    def will_migrate(self):
        self['distance'].stop()
        
    def did_migrate(self):
        self.setup()
    
    @condition([], ['meters'])
    @guard(lambda self: self['distance'].has_data())
    def measure(self):
        distance = self['distance'].read()
        return ActionResult(production=(distance,))

    action_priority = (measure,)
    requires =  ['calvinsys.sensors.distance']


