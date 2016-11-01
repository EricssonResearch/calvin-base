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

from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.io.sensors.enclosure import enclosure

_log = get_logger(__name__)


class Enclosure(object):
    """
        A calvinsys module for getting enclosure data. 
        (Currently only fan data implemented.)

        Requires config in /sensor/enclosure        
    """
    
    INTERVAL = 1.0 # Interval to use in fetching data
    enclosure = None
        
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        self._fan_data = None
        self._power_data = None
        
        self.has_fan_data = False
        self.has_power_data = False
        
        if self._node.attributes.has_private_attribute("/io/sensor/enclosure"):
            # Use runtime specific enclosure configuration
            config = self._node.attributes.get_private("/io/sensor/enclosure")
        else :
            config = None

        if not self.enclosure:
            self.enclosure = enclosure.Enclosure(config)
    
    def identity(self):
        return self.enclosure.identity()
        
    def _trigger(self):
        self._node.sched.trigger_loop(actor_ids=[self._actor])

    def get_fan_data(self):
        assert self.has_fan_data
        return self._fan_data

    def get_power_data(self):
        assert self.has_power_data
        return self._power_data
        
    def ack_fan_data(self):
        self.has_fan_data = False
        self._fan_data = None
        self._fan_active = async.DelayedCall(self.INTERVAL, self.enclosure.get_fan_speed, self.fans, self._receive_fan_data)
        
    def ack_power_data(self):
        self.has_power_data = False
        self._power_data = None
        self._power_active = async.DelayedCall(self.INTERVAL, self.enclosure.get_power_usage, self.power_supplies, self._receive_power_data)

    def _receive_fan_data(self, result):
        self._fan_data = result
        self.has_fan_data = True
        self._trigger()

    def _receive_power_data(self, result):
        self._power_data = result
        self.has_power_data = True
        self._trigger()
        
    def _enabled_cb(self):
        if self.fans:
            self._fan_active = async.DelayedCall(0, self.enclosure.get_fan_speed, self.fans, self._receive_fan_data)
        if self.power_supplies:
            self._power_active = async.DelayedCall(0, self.enclosure.get_power_usage, self.power_supplies, self._receive_power_data)
        self._trigger()
   
    def enable(self, fans=[], power_supplies=[]):
        self.fans = fans
        self.power_supplies = power_supplies
        if self.fans or self.power_supplies:
            self.enclosure.connect(self._enabled_cb)

    def _disable(self):
        if self._fan_active and self._fan_active.active():
            self._fan_active.cancel()
        if self._power_active and self._power_active.active():
            self._power_active.cancel()
        self.enclosure.disconnect()
        
    def disable(self):
        self.enclosure.disconnect()        

def register(node, actor):
    return Enclosure(node, actor)
