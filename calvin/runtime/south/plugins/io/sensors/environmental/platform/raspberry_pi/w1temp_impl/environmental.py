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

import glob
from calvin.runtime.south.plugins.io.sensors.environmental import base_environmental

"""
Read 1-wire temperature sensor. Needs w1-gpio and w1-therm modules:
    modprobe w1-gpio
    modprobe w1-therm
    
    Do not forget to edit /boot/config.txt
        dtoverlay=w1-gpio
"""
    
class Environmental(base_environmental.EnvironmentalBase):

    """
    w1temp temperature sensor
    """

    def __init__(self):
        super(Environmental, self).__init__()
        self._base_dir = '/sys/bus/w1/devices/'
        self._device_folder = glob.glob(self._base_dir + '28*')[0]
        self._device_file = self._device_folder + '/w1_slave'
        self._temperature = None
        
    def _read_temp_raw(self):
        try:
            with open(self._device_file, 'r') as fp:
                return fp.readlines()
        except:
            return None
        
    def _read_temp(self):
        lines = self._read_temp_raw()
        if not lines:
            return 
        if lines and lines[0].strip()[-3:] != 'YES':
            # Nothing to read, will try later
            return

        equals_pos = lines[1].find('t=')
    
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            self._temperature = float(temp_string) / 1000.0
            # Round to nearest half-degree
            self._temperature = round(2*self._temperature, 0)/2.0
        
    def get_temperature(self):
        self._read_temp()
        return self._temperature
            
