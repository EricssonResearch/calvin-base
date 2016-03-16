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

from calvin.runtime.south.plugins.io.sensors.rotary_encoder import rotary_encoder


class RotaryEncoder(object):

    """
    Rotary encoder (aka knob)
    """

    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        self._encoder = rotary_encoder.RotaryEncoder(node, self._knob, self._button)
        self._direction = None
        self._button_pressed = False

    def _knob(self, direction):
        self._direction = direction
        self._node.sched.trigger_loop(actor_ids=[self._actor])
    
    def _button(self):
        self._button_pressed = True
        self._node.sched.trigger_loop(actor_ids=[self._actor])
        
    def was_turned(self):
        return self._direction is not None
        
    def was_pressed(self):
        result = self._button_pressed
        if result:
            self._button_pressed = False
        return result
    
    def read(self):
        result = self._direction
        if result:
            self._direction = None
        return result
        
    def start(self):
        self._encoder.start()
    
    def stop(self):
        self._encoder.stop()
        
        
def register(node=None, actor=None):
    return RotaryEncoder(node, actor)
