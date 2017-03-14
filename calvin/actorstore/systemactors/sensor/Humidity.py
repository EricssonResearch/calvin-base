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

from calvin.actor.actor import Actor, manage, condition


class Humidity(Actor):

    """
    Read Humidity when told to

    Inputs:
        measure: Triggers a temperature reading
    Outputs:
        percent: The measured humidity in percent
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.sensors.environmental", shorthand="humid")

    def will_migrate(self):
        pass

    def did_migrate(self):
        self.setup()

    @condition(['measure'], ['percent'])
    def measure(self, _):
        humidity = self['humid'].get_humidity()
        return (humidity,)

    action_priority = (measure,)
    requires =  ['calvinsys.sensors.environmental']
