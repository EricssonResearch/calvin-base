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

from calvin.runtime.south.calvinsys.io.ky040knob import BaseKY040
from calvin.utilities.calvinlogger import get_logger

import pigpio


_log = get_logger(__name__)


class PIGPIOKY040(BaseKY040.BaseKY040):
    """
    Calvinsys object handling KY-040 rotary encoder using the pigpio package (& daemon)
    """
    def init(self, switch_pin=None, clock_pin=None, data_pin=None, **kwargs):
        self._switch_pin = switch_pin
        self._clock_pin = clock_pin
        self._data_pin = data_pin
        
        self._gpio = pigpio.pi()

        if self._switch_pin:
            self._gpio.set_glitch_filter(self._switch_pin, 2000)
            self._gpio.set_mode(self._switch_pin, pigpio.INPUT)
            self._gpio.set_pull_up_down(self._switch_pin, pigpio.PUD_UP)
            self._switch = self._gpio.callback(self._switch_pin, pigpio.EITHER_EDGE, self._switch_cb)
            
        if self._data_pin:
            self._gpio.set_mode(self._data_pin, pigpio.INPUT)

        if self._clock_pin:
            self._gpio.set_glitch_filter(self._clock_pin, 2000)
            self._gpio.set_mode(self._clock_pin, pigpio.INPUT)
            self._gpio.set_pull_up_down(self._clock_pin, pigpio.PUD_UP)
            self._knob = self._gpio.callback(self._clock_pin, pigpio.FALLING_EDGE, self._knob_cb)

        self._values = []
        
        
    def can_read(self):
        return len(self._values) > 0
        
    def read(self):
        return self._values.pop(0)

    def _knob_cb(self, pin, level, tick):
        if self._gpio.read(self._data_pin) :
            self._values.append(1)
        else :
            self._values.append(-1)
        self.scheduler_wakeup()

    def _switch_cb(self, pin, level, tick):
        val = 1 if level else 0
        if not self._values or self._values[-1] != val:
            self._values.append(val)
            self.scheduler_wakeup()

    def close(self):
        if self._knob : self._knob.cancel()
        if self._switch : self._switch.cancel()
            
        del self._gpio
        self._gpio = None

