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

from calvin.runtime.south.plugins.io.servomotor import base_servomotor
import Adafruit_PCA9685


class ServoMotor(base_servomotor.ServoMotorBase):

    """
    Use adadruits pwm servo driver to control a servo
    """

    def __init__(self):
        self.i2c_addr = 0x40
        self.pin_base = 0x0
        self.pwm = Adafruit_PCA9685.PCA9685()
        self.freq = 60
        self.pwm.set_pwm_freq(self.freq)
        scaling = (1.0 / self.freq / 4096)
        self.servoMin = int(round(.000605 / scaling))
        self.servoCenter = int(round(.00148 / scaling))
        self.servoMax = int(round(.00251 / scaling))

    def set_angle(self, angle):
        if angle >= 0 and angle <= 180:
            self.set_pwm(
                int(round(((self.servoMax - self.servoMin) / 180.) * angle)))

    def set_pwm(self, pulse):
        # Force with in range
        pulse = min(self.servoMax, max(self.servoMin, pulse))
        self.pwm.set_pwm(self.pin_base, 0, pulse)
