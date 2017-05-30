# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.runtime.south.plugins.io.sensors.environmental import base_environmental
import random


def change(old_value, delta, limits):
    new_value = old_value
    if not random.randint(0, 3):
        if random.randint(0, 1):
            new_value += delta
        else :
            new_value -= delta
    if new_value > max(limits):
        new_value = max(limits)
    elif new_value < min(limits):
        new_value = min(limits)
    return new_value

class Environmental(base_environmental.EnvironmentalBase):

    """
    Faked implementation of Environmental
    """
    def __init__(self, node, actor):
        super(Environmental, self).__init__(node, actor)
        self._temp = 21.5
        self._humi = 62.5
        self._pres = 1.015

    def get_temperature(self):
        self._temp = change(self._temp, 0.1, [20, 25])
        return self._temp

    def get_humidity(self):
        self._humi = change(self._humi, 0.5, [60, 85])
        return self._humi

    def get_pressure(self):
        self._press = change(self._press, 0.01, [1.01, 1.02])
        return self._press
