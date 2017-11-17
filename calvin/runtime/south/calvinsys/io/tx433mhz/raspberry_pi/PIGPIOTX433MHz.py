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

from calvin.runtime.south.calvinsys.io.tx433mhz import BaseTX433MHz
from calvin.utilities.calvinlogger import get_logger

try:
    import pigpio
except:
    class GuineaPigpio(object):
        """docstring for GuineaPigpio"""
        OUTPUT = 42
        
        def __init__(self):
            super(GuineaPigpio, self).__init__()
        
        def pi(self):
            return self
            
        def pulse(self, on, off, delay):
            return "{:x}/{:x}/{}".format(on, off, delay)    
        
        def set_mode(self, *args):
            pass
        
        def wave_tx_busy(self):
            return False
            
        def wave_clear(self):
            pass
            
        def wave_add_generic(self, wf):
            self.wf = wf
            
        def wave_create(self):
            return self.wf
            
        def wave_send_once(self, seq):
            print ", ".join(seq)

        def wave_chain(self, control):
            while control:
                x = control.pop(0)
                if x != 255:
                    self.wave_send_once(x)
                    continue
                cmd = control.pop(0)
                if cmd==0 or cmd==3:
                    print "CMD", cmd
                    continue
                if cmd==1 or cmd==2:
                    arg = control.pop(0) + 256 * control.pop(0)
                    print "CMD", cmd, arg
                    continue
                raise Exception("Bad command")

    pigpio = GuineaPigpio()


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

if __name__ == '__main__':
   d = PIGPIOTX433MHz(None, None, None)
   d.init(18)
   print d
   print d.can_write()
   d.write([(1, 1), (0, 10), (1, 1), (0, 1), (1, 1), (0, 5)])
   
