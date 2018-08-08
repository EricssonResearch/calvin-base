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

from calvinextras.calvinsys.io.ky040knob import BaseKY040
from calvin.utilities.calvinlogger import get_logger
import RPi.GPIO as gpio

_log = get_logger(__name__)


class GPIOKY040(BaseKY040.BaseKY040):
    """
    Calvinsys object handling KY-040 rotary encoder using the RPi.GPIO package
    """
    def init(self, switch_pin=None, clock_pin=None, data_pin=None, **kwargs):
        _log.info("setup")
        self._switch_pin = switch_pin
        self._clock_pin = clock_pin
        self._data_pin = data_pin
        
        gpio.setmode(gpio.BCM)

        if self._switch_pin:
            _log.info("Setting up button pin")
            gpio.setup(self._switch_pin, gpio.IN, gpio.PUD_UP)
            gpio.add_event_detect(self._switch_pin, gpio.BOTH, callback=self._switch_cb, bouncetime=2)
            
        if self._data_pin:
            _log.info("Setting up data pin")
            gpio.setup(self._data_pin, gpio.IN)

        if self._clock_pin:
            gpio.setup(self._clock_pin, gpio.IN, gpio.PUD_UP)
            gpio.add_event_detect(self._clock_pin, gpio.FALLING, callback=self._knob_cb, bouncetime=2)
            
        self._values = []
        
        _log.info("Systems are go")
        
    def can_read(self):
        return len(self._values) > 0
        
    def read(self):
        return self._values.pop(0)

    def _knob_cb(self, pin):
        if gpio.input(self._data_pin) is gpio.HIGH :
            self._values.append(1)
        else :
            self._values.append(-1)
        self.scheduler_wakeup()

    def _switch_cb(self, pin):
        if gpio.input(self._data_pin) is gpio.HIGH:
            val = 1
        else :
            val = 0
        if not self._values or self._values[-1] != val:
            self._values.append(val)
            self.scheduler_wakeup()

        
    def close(self):
        if self._clock.pin:
            gpio.cleanup(self._clock_pin)
        if self._switch_pin:
            gpio.cleanup(self._switch_pin)
        if self._data_pin:
            gpio.cleanup(self._data_pin)

