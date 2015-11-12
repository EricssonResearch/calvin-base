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

from sense_hat import SenseHat
from calvin.runtime.south.plugins.io.sensors.environmental import base_environmental


class Environmental(base_environmental.EnvironmentalBase):

    """
    Raspberry Pi Sense HAT environmental sensors
    """

    def __init__(self):
        self.sense = SenseHat()

    def get_temperature(self):
        return self.sense.get_temperature()

    def get_humidity(self):
        return self.sense.get_humidity()

    def get_pressure(self):
        return self.sense.get_pressure()
