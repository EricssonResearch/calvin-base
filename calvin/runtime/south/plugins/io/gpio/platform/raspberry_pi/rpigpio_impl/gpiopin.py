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

import time
import RPi.GPIO as GPIO
from calvin.runtime.south.plugins.io.gpio import base_gpiopin


class GPIOPin(base_gpiopin.GPIOPinBase):
    """
    Raspberry Pi gpio pin implementation based on the RPi.GPIO package
    """
    def __init__(self, trigger, pin, direction, pull):
        super(GPIOPin, self).__init__(trigger, pin, direction, pull)
        self.trigger = trigger
        self.pin = pin
        self.has_changed = False
        self.value = None
        self.pwm = None

        GPIO.setmode(GPIO.BCM)

        if direction == "i":
            if pull is not None:
                if pull == "u":
                    GPIO.setup(pin, GPIO.IN, GPIO.PUD_UP)
                elif pull == "d":
                    GPIO.setup(pin, GPIO.IN, GPIO.PUD_DOWN)
            else:
                GPIO.setup(pin, GPIO.IN)
        elif direction == "o":
            GPIO.setup(pin, GPIO.OUT)

    def cb_detect_edge(self, channel):
        self.has_changed = True
        if GPIO.input(self.pin) is GPIO.LOW:
            self.value = 0
        else:
            self.value = 1
        self.trigger()

    def detect_edge(self, edge):
        if edge == "r":
            GPIO.add_event_detect(self.pin, GPIO.RISING, callback=self.cb_detect_edge)
        elif edge == "f":
            GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=self.cb_detect_edge)
        elif edge == "b":
            GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.cb_detect_edge)

    def stop_detect(self):
        GPIO.remove_event_detect(self.pin)
        
    def edge_detected(self):
        return self.has_changed

    def edge_value(self):
        self.has_changed = False
        return self.value

    def set_state(self, state):
        if state:
            GPIO.output(self.pin, GPIO.HIGH)
        else:
            GPIO.output(self.pin, GPIO.LOW)

    def get_state(self):
        if GPIO.input(self.pin) is GPIO.LOW:
            return 0
        return 1

    def pwm_start(self, frequency, dutycycle):
        self.pwm = GPIO.PWM(self.pin, frequency)
        self.pwm.start(dutycycle)

    def pwm_set_frequency(self, frequency):
        self.pwm.ChangeFrequency(frequency)

    def pwm_set_dutycycle(self, dutycycle):
        self.pwm.ChangeDutyCycle(dutycycle)

    def pwm_stop(self):
        self.pwm.stop()

    def shift_out(self, data, repeat):
        for x in range(0, repeat):
            for bit in data:
                GPIO.output(self.pin, bit[0])
                time.sleep(bit[1]/1000000.0)

    def close(self):
        GPIO.cleanup(self.pin)
