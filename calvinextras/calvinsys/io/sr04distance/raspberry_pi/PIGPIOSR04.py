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

from calvinextras.calvinsys.io.sr04distance import BaseSR04
from calvin.runtime.south.async import async

from calvin.utilities.calvinlogger import get_logger
import pigpio

_log = get_logger(__name__)

class PIGPIOSR04(BaseSR04.BaseSR04):
    """
    Calvinsys object handling SR04 distance sensor using the pigpio package (& daemon)
    """
    def init(self, echo_pin, trigger_pin, **kwargs):
        self._echo_pin = echo_pin
        self._trigger_pin = trigger_pin

        self._gpio = pigpio.pi()
        self._gpio.set_mode(self._trigger_pin, pigpio.OUTPUT)
        self._gpio.set_mode(self._echo_pin, pigpio.INPUT)
        self._gpio.set_pull_up_down(self._echo_pin, pigpio.PUD_DOWN)

        self._elapsed = None
        self._detection = None

    def _edge_cb(self, pin, edge, tick):
        self._gpio.set_watchdog(self._echo_pin, 0)
        if edge == pigpio.TIMEOUT :
            _log.debug("echo timeout exceded")
        self._elapsed = pigpio.tickDiff(self._t0, tick)
        self._detection.cancel()
        async.call_from_thread(self.scheduler_wakeup)


    def can_write(self):
        return self._detection is None


    def write(self, _):
        # trigger measurement
        self._detection = self._gpio.callback(self._echo_pin, pigpio.FALLING_EDGE, self._edge_cb)
        self._gpio.set_watchdog(self._echo_pin, 1000)
        self._t0 = self._gpio.get_current_tick()
        self._gpio.gpio_trigger(self._trigger_pin, 50, 1)


    def can_read(self):
        return self._elapsed is not None

    def read(self):
        # distance is (elapsed us) * (speed of sound in mm/usec, 0.343)/2
        distance = self._elapsed*0.343/2 # not great accuracy
        self._elapsed = None
        self._detection = None
        # Return value in meters rather than mm
        return distance/1000.0


    def close(self):
        del self._gpio
        self._gpio = None

