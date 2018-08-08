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

from calvinextras.calvinsys.io.ky040knob import BaseKY040
from calvin.utilities.calvinlogger import get_logger

import pigpio


_log = get_logger(__name__)


class PIGPIOKY040(BaseKY040.BaseKY040):
    """
    Calvinsys object handling KY-040 rotary encoder using the pigpio package (& daemon)
    """
    AF = 0
    AR = 1
    BF = 2
    BR = 3

    CW = 1
    CCW = -1

    # The rotary encoder progress through a state sequence for each "click"
    # 3 -> 1 -> 0 -> 2 -> 3 (Counter Clock Wise, CCW), or
    # 3 -> 2 -> 0 -> 1 -> 3 (Clock Wise, CCW)
    # The code generates an output signal (CW or CCW) when leaving state 0,
    # as defined by state handlers below
    handlers = [{AR:(2, CCW), BR:(1, CW)}, {BF:(0, None), AR:(3, None)}, {BR:(3, None), AF:(0, None)}, {AF:(1, None), BF:(2, None)}]
    # The dicts in the array corresponds to state 0 through 3, and each dict have two keys corresponding to
    # the allowed input signals for that state. The tuple value for each signal key consists of (next_state, output)

    # signals = ['AF', 'BF', 'AR', 'BR']

    def init(self, switch_pin=None, clock_pin=None, data_pin=None, **kwargs):
        self._switch_pin = switch_pin
        self._clock_pin = clock_pin
        self._data_pin = data_pin
        self._state = 0
        self._gpio = pigpio.pi()
        self._data = None
        self._clock = None
        self._switch = None

        if self._switch_pin:
            self._gpio.set_glitch_filter(self._switch_pin, 2000)
            self._gpio.set_mode(self._switch_pin, pigpio.INPUT)
            self._gpio.set_pull_up_down(self._switch_pin, pigpio.PUD_UP)
            self._switch = self._gpio.callback(self._switch_pin, pigpio.EITHER_EDGE, self._switch_cb)

        if self._data_pin:
            self._gpio.set_mode(self._data_pin, pigpio.INPUT)
            self._data = self._gpio.callback(self._data_pin, pigpio.EITHER_EDGE, self._data_cb)

        if self._clock_pin:
            self._gpio.set_mode(self._clock_pin, pigpio.INPUT)
            self._clock = self._gpio.callback(self._clock_pin, pigpio.EITHER_EDGE, self._clock_cb)

        if self._data_pin and self._clock_pin:
            self._state = 2*self._gpio.read(self._clock_pin) + self._gpio.read(self._data_pin)

        self._values = []


    def can_read(self):
        return len(self._values) > 0

    def read(self):
        return self._values.pop(0)

    def _clock_cb(self, pin, level, tick):
        # signal: (AF) Falling = 0, (AR) Rising = 1
        signal = level
        self.update_state(signal)

    def _data_cb(self, pin, level, tick):
        # signal: (BF) Falling = 2, (BR) Rising = 3
        signal = level + 2
        self.update_state(signal)

    def update_state(self, signal):
        # Get the handler for the current state
        handler = self.handlers[self._state]
        # Get next state and output (if any) based on signal,
        # illegal transitions set both next state and output to None
        next_state, output = handler.get(signal, (None, None))
        if next_state is not None:
            # _log.info("{} => {} --> {} {}".format(self.signals[signal], self._state, next_state, output))
            self._state = next_state
            if output is not None:
                self._values.append(output)
                self.scheduler_wakeup()
        # else:
        #     _log.info("BAD TRANSITION. {} in state {}".format(self.signals[signal], self._state))


    def _switch_cb(self, pin, level, tick):
        val = 1 if level else 0
        if not self._values or self._values[-1] != val:
            self._values.append(val)
            self.scheduler_wakeup()

    def close(self):
        if self._data : self._data.cancel()
        if self._clock : self._clock.cancel()
        if self._switch : self._switch.cancel()

        del self._gpio
        self._gpio = None

