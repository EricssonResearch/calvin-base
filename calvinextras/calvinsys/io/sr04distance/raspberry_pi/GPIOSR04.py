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
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.async import async

import time
import RPi.GPIO as gpio

_log = get_logger(__name__)

class GPIOSR04(BaseSR04.BaseSR04):
    """
    Calvinsys object handling SR04 distance sensor using the RPi.GPIO package
    """
    def init(self, echo_pin, trigger_pin, **kwargs):
        self._echo_pin = echo_pin
        self._trigger_pin = trigger_pin

        gpio.setmode(gpio.BCM)
        gpio.setup(self._echo_pin, gpio.IN, gpio.PUD_UP)
        gpio.setup(self._trigger_pin, gpio.OUT)

        self._elapsed = None
        self._detection = None

    def can_write(self):
        return self._detection is None

    def _trigger(self):
        try :
            self._detection = True
            self._t0 = time.time()
            gpio.output(self._trigger_pin, gpio.HIGH)
            time.sleep(0.00005)
            gpio.output(self._trigger_pin, gpio.LOW)
            pin = gpio.wait_for_edge(self._echo_pin, gpio.FALLING, timeout=1000)
            self._elapsed = time.time() - self._t0

            if pin is None:
                _log.debug("echo timeout exceeded") #

            self._detection = None
            async.call_from_thread(self.scheduler_wakeup)


        except Exception as e:
            _log.warning("Failed sonar triggering: {}".format(e))

    def write(self, _):
        # trigger measurement
        async.call_from_thread(self._trigger)

    def can_read(self):
        # measurement done
        return self._elapsed is not None

    def read(self):
        # elapsed in secs
        # distance = (elapsed s) * (speed of sound in mm/s) / 2
        distance = self._elapsed*343*1000/2 # not great accuracy
        self._elapsed = None
        self._detection = None
        return distance

    def close(self):
        gpio.cleanup(self._trigger_pin)
        gpio.cleanup(self._echo_pin)

