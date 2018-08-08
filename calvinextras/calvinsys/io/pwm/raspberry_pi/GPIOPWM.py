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
import RPi.GPIO as GPIO

class GPIOPWM(BasePWM.BasePWM):
    """
    Calvinsys object handling PWM for a pin using the RPi.GPIO package
    """
    def init(self, pin,frequency, dutycycle, **kwargs):
        self._pin = pin
        self._dutycycle = dutycycle
        self._frequency = frequency
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.OUT)
        
        self._pwm = GPIO.PWM(self._pin, self._frequency)
        self._pwm.start(self._dutycycle)

    def can_write(self):
        return self._pwm is not None


    def write(self, dutycycle):
        self._dutycycle = dutycycle
        self._pwm.ChangeDutyCycle(self._dutycycle)

    def close(self):
        GPIO.cleanup(self._pin)
        self._pwm = None
