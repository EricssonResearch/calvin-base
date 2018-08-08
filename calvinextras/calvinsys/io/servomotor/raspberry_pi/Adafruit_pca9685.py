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

from calvinextras.calvinsys.io.servomotor import BaseServo
import Adafruit_PCA9685


class Adafruit_pca9685(BaseServo.BaseServo):
    """
    Calvinsys object handling servo using ADAFRUIT PCA9685
    """
    def init(self, angle, frequency, minimum_pulse, maximum_pulse, *args, **kwargs):
        self._i2c_addr = kwargs.get("i2c_addr", 0x40)
        self._pin_base = kwargs.get("pin_base", 0x0)
        self._bus_num = kwargs.get("bus_num", 1)
        
        self._angle = angle
        
        self._minimum_pulse = minimum_pulse
        self._maximum_pulse = maximum_pulse
        
        self._pwm = Adafruit_PCA9685.PCA9685(address=self._i2c_addr, busnum=self._bus_num)
        self._frequency = frequency
        self._pwm.set_pwm_freq(self._frequency)

        scaling = (1.0 / self._frequency / 4096 * 10**6)
        
        self._servo_min = int(round(self._minimum_pulse / scaling))
        self._servo_max = int(round(self._maximum_pulse / scaling))
                
    def can_write(self):
        return self._pwm is not None
    
    def write(self, angle_or_pulse):
        if self._angle:
            return self._set_angle(angle_or_pulse)
        else :
            return self._set_pulse(angle_or_pulse)

    def _set_angle(self, angle):
        if angle < 0 :
            angle = 0
        elif angle > 180:
            angle = 180

        self._set_pwm(int(round(((self._servo_max - self._servo_min) / 180.) * angle)))

    def _set_pwm(self, pulse):
        # Force with in range
        pulse = min(self._servo_max, max(self._servo_min, pulse))
        self._pwm.set_pwm(self._pin_base, 0, pulse)
        
    def close(self):
        self._pwm = None