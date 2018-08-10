
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

from calvin.runtime.south.calvinsys import base_calvinsys_object
import sensehat
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class SenseHatSensor(base_calvinsys_object.BaseCalvinsysObject):
    """
    Use Raspberry Pi SenseHat sensors.

    Currently supports temperature (in centigrade), pressure (in millibars) and relative humidity (in %)
    """
    init_schema = {
        "description": "Initialize which SenseHat sensor to use",
        "type": "object",
        "properties": {
            "sensor":  {
                "description": "What to measure",
                "type": "string",
                "enum": ["temperature", "pressure", "humidity"]
            },
            "precision": {
                "description": "number of decimals to include in measurement",
                "type": "integer",
                "minimum": 0,
                "maximum": 10
            }
        },
        "required": ["sensor"]
    }

    can_write_schema = {
        "description": "True iff SenseHat configured and ready",
        "type": "boolean"
    }

    write_schema = {
        "description": "Initiate reading selected sensor",
        "type": ["boolean", "null", "number", "integer"]
    }

    can_read_schema =  {
        "description": "True when value ready for reading",
        "type": "boolean"
    }

    read_schema = {
        "description": "Latest reading for selected sensor",
        "type": "number"
    }

    def init(self, sensor, precision=2):
        self._sensor = sensor
        self._precision=precision
        self._sensehat = sensehat.SenseHat()
        self._can_read = False
        self._can_write = True
        self._value = None

    def can_write(self):
        return self._can_write

    def can_read(self):
        return self._can_read

    def write(self, _=None):
        def set_value(value, *args, **kwargs):
            if isinstance(value, float) or isinstance(value, int):
                self._value = int((10**self._precision*value))/10.0**self._precision
            else:
                _log.warning("Failed reading '{}' from sensehat: {}".format(self._sensor, value))
                self._value = None
            self._can_read = True
            self.scheduler_wakeup()

        {
            "temperature": self._sensehat.read_temperature,
            "pressure": self._sensehat.read_pressure,
            "humidity": self._sensehat.read_humidity
        }.get(self._sensor)(set_value)


    def read(self):
        self._can_read = False
        self._can_write = True
        return self._value

    def close(self):
        self._can_read = False
        self._can_write = False
        self._sensehat = None
