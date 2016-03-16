# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.runtime.south.plugins.io.sensors.rotary_encoder import base_rotary_encoder
from calvin.runtime.south.plugins.async import async
from calvin.runtime.south.plugins.io.gpio import gpiopin

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class RotaryEncoder(base_rotary_encoder.RotaryEncoderBase):

    """
        KY040 Rotary Encoder
    """
    def __init__(self, node, turn_callback, switch_callback):
        super(RotaryEncoder, self).__init__(node, turn_callback, switch_callback)        
        self._running = False
        self._node = node
        self._turn_callback = turn_callback
        self._switch_callback = switch_callback
        
        config = self._node.attributes.get_private("/hardware/ky040_rotary_encoder")
        clk_pin = config.get('clk_pin', None)
        dt_pin = config.get('dt_pin', None)
        sw_pin = config.get('sw_pin', None)

        self._clk_pin = gpiopin.GPIOPin(self._knob, clk_pin, "i", "u")
        self._dt_pin = gpiopin.GPIOPin(None, dt_pin, "i", None)
        self._sw_pin = gpiopin.GPIOPin(self._switch, sw_pin, "i", "u")
  
    def start(self, frequency=0.5):
        try :
            self._clk_pin.detect_edge("f")
            self._sw_pin.detect_edge("f")
            self._running = True
            # gpio.add_event_detect(self.echo_pin,
            #                      gpio.FALLING,
            #                      callback=self._echo_callback)
        except Exception as e:
            _log.error("Could not setup event detect: %r" % (e, ))

    def cb_error(self, *args, **kwargs):
        _log.error("%r: %r" % (args, kwargs))

    def _knob(self):
        if self._clk_pin.get_state():
            if self._dt_pin.get_state() :
                async.call_from_thread(self._turn_callback, -1)
            else :
                async.call_from_thread(self._turn_callback, 1)

    def _switch(self):
        async.call_from_thread(self._switch_callback)

        
    def stop(self):
        if self._running :
            if self.retry and self.retry.iactive() :
                self.retry.cancel()
            try:
                self._sw_pin.stop_detect()
                self._dt_pin.stop_detect()
                self._clk_pin.stop_detect()
            except Exception as e:
                _log.warning("Could not remove event detect: %r" % (e,))
            self._running = False

