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

from calvin.actor.actor import Actor, condition


class TrainTrackSwitch(Actor):

    """
    Switch train track using servo.
    Input:
      switch : triggers switch
    """

    def init(self):
        self.setup()
        self.track = 0
        self.servo.set_angle(75)

    def setup(self):
        self.use("calvinsys.io.servomotor", shorthand="servohandler")
        self.servo = self["servohandler"]

    @condition(action_input=("switch",))
    def set_track(self, switch):
        if self.track == 0:
            self.servo.set_angle(85)
            self.track = 1
        else:
            self.servo.set_angle(75)
            self.track = 0

    action_priority = (set_track, )
    requires = ["calvinsys.io.servomotor"]
