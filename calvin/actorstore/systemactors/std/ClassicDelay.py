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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class ClassicDelay(Actor):
    """
    After first token, pass on token once every 'delay' seconds.
    Input :
        token: anything
    Outputs:
        token: anything
    """

    @manage(['delay'])
    def init(self, delay=0.1):
        self.delay = delay
        self.use('calvinsys.events.timer', shorthand='timer')
        self.timer = None

    def setup(self):
        self.timer = self['timer'].repeat(self.delay)

    def will_migrate(self):
        self.timer.cancel()

    def did_migrate(self):
        self.setup()

    @condition(['token'], ['token'])
    @guard(lambda self, _: not self.timer)
    def start_timer(self, token):
        self.setup()
        return ActionResult(production=(token, ))

    @condition(['token'], ['token'])
    @guard(lambda self, _: self.timer and self.timer.triggered)
    def passthrough(self, token):
        self.timer.ack()
        return ActionResult(production=(token, ))

    action_priority = (start_timer, passthrough)
    requires = ['calvinsys.events.timer']
