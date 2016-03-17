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

from calvin.runtime.south.plugins.io.sensors.environmental import environmental


class Environmental(object):

    """
    Environmental sensor
    """

    def __init__(self):
        self.sensor = environmental.Environmental()

    def get_temperature(self):
        """
        Get temperature from sensor
        """
        return self.sensor.get_temperature()

    def get_humidity(self):
        """
        Get humidity from sensor
        """
        return self.sensor.get_humidity()

    def get_pressure(self):
        """
        Get pressure from sensor
        """
        return self.sensor.get_temperature()


def register(node=None, actor=None):
    """
        Called when the system object is first created.
    """
    return Environmental()
