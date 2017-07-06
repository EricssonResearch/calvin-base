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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys


class ClassicDelay(Actor):
    """
    After first token, pass on token once every 'delay' seconds.
    Input :
        token: anything
    Outputs:
        token: anything
    """

    @manage(['delay', 'started'])
    def init(self, delay=0.1):
        self.delay = delay
        self.started = False
        self.setup()

    def setup(self):
        self._timer = calvinsys.open(self, "sys.timer.repeating")

    def start(self):
        calvinsys.write(self._timer, self.delay)
        self.started = True

    def will_migrate(self):
        if self._timer:
            calvinsys.close(self._timer)

    def did_migrate(self):
        self.setup()
        if self.started:
            self.start()

    @stateguard(lambda self: not self.started)
    @condition(['token'], ['token'])
    def start_timer(self, token):
        self.start()
        return (token, )

    @stateguard(lambda self: self._timer and calvinsys.can_read(self._timer))
    @condition(['token'], ['token'])
    def passthrough(self, token):
        calvinsys.read(self._timer)
        return (token, )

    action_priority = (start_timer, passthrough)
    requires = ['sys.timer.repeating']
