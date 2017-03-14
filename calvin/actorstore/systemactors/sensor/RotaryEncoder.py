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


class RotaryEncoder(Actor):

    """
    Read a knob to see which way it turned.

    Outputs:
        direction: clockwise or anti-clockwise
        button: True if button was pressed
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.sensors.rotary_encoder", shorthand="knob")
        self['knob'].start()

    def will_migrate(self):
        self['knob'].stop()

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self['knob'].was_pressed())
    @condition([], ['button'])
    def button(self):
        return (True,)

    @stateguard(lambda self: self['knob'].was_turned())
    @condition([], ['direction'])
    def turn(self):
        direction = "clockwise" if self['knob'].read() == 1 else "anti-clockwise"
        return (direction,)

    action_priority = (turn, button,)
    requires =  ['calvinsys.sensors.rotary_encoder']


