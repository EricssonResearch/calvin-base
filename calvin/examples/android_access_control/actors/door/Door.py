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

from calvin.actor.actor import Actor, manage, condition, stateguard
class Door(Actor):
    """
    Creates a door actor that controls a servo.

    Input:
      open_door : Open the door
      close_door   : Close the door
    """
    
    @manage([])
    def init(self, channel=0):
        self.setup()
    
    def setup(self):
        self.use("calvinsys.io.servo", shorthand="servo")
        self.servo = self["servo"]
    	self.channel = channel

    def did_migrate(self):
        self.setup()

    def will_end(self):
        pass

    @stateguard(lambda self: self.servo)
    @condition(["open_door"], [])
    def open_door(self, data):
	self.servo.set_servo(590, self.channel)
    
    @stateguard(lambda self: self.servo)
    @condition(["close_door"], [])
    def close_door(self, data):
	self.servo.set_servo(25, self.channel)
    
    action_priority = (open_door, close_door)
    requires = ['calvinsys.io.servo']
    
    
