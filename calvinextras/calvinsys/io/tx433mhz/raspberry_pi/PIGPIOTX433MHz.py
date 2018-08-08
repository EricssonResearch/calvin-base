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

from calvinextras.calvinsys.io.tx433mhz import BaseTX433MHz
from calvin.utilities.calvinlogger import get_logger
import pigpio


_log = get_logger(__name__)


class PIGPIOTX433MHz(BaseTX433MHz.BaseTX433MHz):
    """
    Calvinsys object handling 433Mhz transmitters using the pigpio package (& daemon)
    """
    def init(self, pin, repeat, **kwargs):
        self._pin = pin 
        self._repeat = repeat & 0xFF
        self._gpio = pigpio.pi()
        self._gpio.set_mode(self._pin, pigpio.OUTPUT)

    def can_write(self):
        busy = self._gpio is None or self._gpio.wave_tx_busy()
        return not busy  
        
    def _make_waveform(self, waveform):
        wf = []
        # Bit mask for GPIO pin number
        pin = 1<<self._pin
        # Convert to waveformat required by pigpio 
        for val, t in waveform:
            if val: 
                wf.append(pigpio.pulse(pin, 0, t))
            else:
                wf.append(pigpio.pulse(0, pin, t))
        return wf             

    def write(self, waveform):
        """waveform is list [(bit, delay in us), (bit, delay in us), ...]"""
        wf = self._make_waveform(waveform)
        self._gpio.wave_clear()
        self._gpio.wave_add_generic(wf)
        seq = self._gpio.wave_create()
        self._gpio.wave_chain([255, 0, seq, 255, 2, 0x88, 0x13, 255, 1, self._repeat, 0])

    def close(self):
        del self._gpio
        self._gpio = None
   
