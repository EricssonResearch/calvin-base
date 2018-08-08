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

from calvinextras.calvinsys.io.pwm import BasePWM
import pigpio

class PIGPIOPWM(BasePWM.BasePWM):
    """
    Calvinsys object handling PWM for a pin using the pigpio package (& daemon)
    """
    def init(self, pin,frequency, dutycycle, **kwargs):
        self._pin = pin
        self._dutycycle = dutycycle
        self._frequency = frequency
        
        self._gpio = pigpio.pi()
        self._gpio.set_mode(self._pin, pigpio.OUTPUT)
        
        self._gpio.set_PWM_range(self._pin, 100)# pigpio uses default dc range [0, 255]
        self._gpio.set_PWM_frequency(self._pin, self._frequency)
        self._gpio.set_PWM_dutycycle(self._pin, self._dutycycle)

    def can_write(self):
        return self._gpio is not None

    def write(self, dutycycle):
        self._dutycycle = dutycycle
        self._gpio.set_PWM_dutycycle(self._pin, self._dutycycle)

    def close(self):
        del self._gpio
        self._gpio = None

