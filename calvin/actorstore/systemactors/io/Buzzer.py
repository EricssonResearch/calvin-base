# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

from calvin.actor.actor import Actor, manage, condition, calvinsys


class Buzzer(Actor):

    """
    Buzz
    Input:
      volume : 0-100 (%)
    """

    @manage(["volume"])
    def init(self):
        self._volume = None
        self.setup()

    def setup(self):
        self.buzzer = calvinsys.open(self, "calvinsys.io.buzzer")
        if self._volume and calvinsys.can_write(self.buzzer):
            calvinsys.write(self.buzzer, self._volume)

    def will_migrate(self):
        calvinsys.close(self.buzzer)
        self.buzzer = None

    def will_end(self):
        if self.buzzer :
            calvinsys.close(self.buzzer)

    def did_migrate(self):
        self.setup()

    @condition(["volume"], [])
    def set_volume(self, volume):
        try:
            vol = int(volume)
            if vol < 0 : vol = 0
            if vol > 100: vol = 100
            self._volume = vol
        except Exception:
            self._volume = 0
            
        if calvinsys.can_write(self.buzzer):
            calvinsys.write(self.buzzer, self._volume)

    action_priority = (set_volume, )
    requires = ["calvinsys.io.buzzer"]
