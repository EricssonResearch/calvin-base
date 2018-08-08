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

from calvinextras.calvinsys.io.gpiopin import BaseGPIOPin
import RPi.GPIO as GPIO

class RPiGPIOPin(BaseGPIOPin.BaseGPIOPin):
    """
    Calvinsys object handling a general-purpose input/output pin using the RPi.GPIO package
    """
    def init(self, pin, direction, pull=None, edge=None, bouncetime=None, **kwargs):
        self.values = []
        self.pin = pin
        self.direction = direction
        self.edge = edge
        GPIO.setmode(GPIO.BCM)
        if direction == "IN":
            if pull is not None:
                if pull == "UP":
                    GPIO.setup(pin, GPIO.IN, GPIO.PUD_UP)
                elif pull == "DOWN":
                    GPIO.setup(pin, GPIO.IN, GPIO.PUD_DOWN)
                else:
                    raise Exception("Uknown pull configuration")
            else:
                GPIO.setup(pin, GPIO.IN)

            if edge is not None:
                if edge == "RISING":
                    GPIO.add_event_detect(self.pin, GPIO.RISING, callback=self.edge_cb, bouncetime=bouncetime)
                elif edge == "FALLING":
                    GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=self.edge_cb, bouncetime=bouncetime)
                elif edge == "BOTH":
                    GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.edge_cb, bouncetime=bouncetime)
                else:
                    raise Exception("Unknown edge configuration")
        elif direction == "OUT":
            GPIO.setup(pin, GPIO.OUT)
        else:
            raise Exception("Unknown direction")

    def edge_cb(self, channel):
        if GPIO.input(self.pin) is GPIO.LOW:
            value = 0
        else:
            value = 1
        self.values.append(value)
        self.scheduler_wakeup()

    def can_write(self):
        return self.direction == "OUT"

    def write(self, value):
        if value:
            GPIO.output(self.pin, GPIO.HIGH)
        else:
            GPIO.output(self.pin, GPIO.LOW)

    def can_read(self):
        if self.direction == "IN":
            if self.edge is None:
                return True
            if self.values :
                return True
        return False

    def read(self):
        if self.values :
            value = self.values.pop(0)
        else:
            value = 0 if GPIO.input(self.pin) is GPIO.LOW else 1
        return value

    def close(self):
        self.direction = ""
        GPIO.cleanup(self.pin)
