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

from extras.calvinsys.io.ds18b20thermometer.BaseDS18B20 import BaseDS18B20
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import async
import glob

_log = get_logger(__name__)

class DS18B20(BaseDS18B20):
    """
    Calvinsys object handling DS18B20 temperature sensor
    """
    def init(self, **kwargs):
        self._base_dir = '/sys/bus/w1/devices/'
        self._temperature = None
        self._device_file = self._find_device_file()
        self._in_progress = None

    def _find_device_file(self):
        try :
            device_folder = glob.glob(self._base_dir + '28*')[0]
            device_file = device_folder + '/w1_slave'
        except Exception as e:
            _log.warning("Failed to find device file: {}".format(e))
            device_file = None
        return device_file


    def _read_temp_raw(self):
        try:
            with open(self._device_file, 'r') as fp:
                return fp.readlines()
        except:
            return None

    def _read_temp(self):
        lines = self._read_temp_raw()
        if not lines or lines[0].strip()[-3:] != 'YES':
            # Nothing to read, try again in a second
            self._in_progress = async.DelayedCall(1.0, self._read_temp)
            return

        equals_pos = lines[1].find('t=')

        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            self._temperature = float(temp_string)/1000.0
            self._temperature = self._temperature
        else :
            self._in_progress = async.DelayedCall(1.0, self._read_temp)

        # clear in_progress
        self._in_progress = None


    def _start_read(self):
        async.call_from_thread(self._read_temp)

    def can_write(self):
        return self._in_progress is None

    def write(self, measure):
        self._in_progress = async.DelayedCall(0.0, self._read_temp)

    def can_read(self):
        return self._temperature is not None

    def read(self):
        temperature = self._temperature
        self._temperature = None
        return temperature

    def close(self):
        self._device_file = None

