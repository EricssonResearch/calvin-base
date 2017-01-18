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

from calvin.actor.actor import Actor, condition


class Humidity(Actor):

    """
    Output humidity
    Inputs:
      trigger: Trigger reading
    Outputs:
      humidity:  { "value" : <value>, "unit": <unit>}
    """

    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.sensors.environmental", shorthand="sensor")
        self.sensor = self["sensor"]

    def did_migrate(self):
        self.setup()

    @condition(action_input=["trigger"], action_output=["humidity"])
    def get_humidity(self, input):
        result = {}
        result['value'] = self.sensor.get_humidity()
        result['value'] = int(result['value'])
        result['unit'] = "%"
        
        return (result, )

    action_priority = (get_humidity, )
    requires = ["calvinsys.sensors.environmental"]
