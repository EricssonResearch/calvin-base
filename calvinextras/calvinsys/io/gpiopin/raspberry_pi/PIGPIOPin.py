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
from calvin.utilities.calvinlogger import get_logger
import pigpio

_log = get_logger(__name__)

class PIGPIOPin(BaseGPIOPin.BaseGPIOPin):
    """
    Calvinsys object handling a general-purpose input/output pin using the RPi.GPIO package
    """
    
    PULL = {"up": pigpio.PUD_UP, "down": pigpio.PUD_DOWN, "off": pigpio.PUD_OFF}
    MODE = {"in": pigpio.INPUT, "out": pigpio.OUTPUT}
    EDGE = {"rising": pigpio.RISING_EDGE, "falling": pigpio.FALLING_EDGE, "both": pigpio.EITHER_EDGE}
    
    def init(self, pin, direction, pull=None, edge=None, bouncetime=None, **kwargs):
        self._values = []
        self._pin = pin
        self._direction = direction
        self._debounce = 1000*bouncetime if bouncetime else None # bouncetime is ms, pigpio uses us
        self._edge = edge
        self._gpio = pigpio.pi()
        self._cb = None
        
        try :
            mode = self.MODE[direction.lower()]
        except KeyError:
            raise Exception("Unknown direction '{}', should be IN, OUT".format(direction))
        
        if mode == pigpio.INPUT:
            try:
                pud = self.PULL[pull.lower()] if pull else pigpio.PUD_OFF
            except KeyError:
                raise Exception("Unknown pull '{}', should be UP, DOWN, OFF".format(pull))
            self._gpio.set_pull_up_down(pin, pud)
            if self._debounce:
                self._gpio.set_glitch_filter(pin, self._debounce)
            
        self._gpio.set_mode(pin, mode)


        if edge is not None:
            try:
                detect = self.EDGE[edge.lower()]
            except KeyError:
                raise Exception("Unknown edge '{}', should be RISING, FALLING, BOTH")
            self._cb = self._gpio.callback(pin, detect, self._edge_cb)

    def _edge_cb(self, pin, edge, tick):
        if edge != 2:
            self._values.append(edge)
            self.scheduler_wakeup()

    def can_write(self):
        return self._direction.lower() == "out"

    def write(self, value):
        self._gpio.write(self._pin, 1 if value else 0)

    def can_read(self):
        if self._direction.lower() == 'in':
            return bool(self._values)
        return False

    def read(self):
        if self._values:
            return self._values.pop(0)
        else:
            return self._gpio.read(self._pin)

    def close(self):
        if self._cb:
            self._cb.cancel()
        del self._gpio
        self._gpio = None
