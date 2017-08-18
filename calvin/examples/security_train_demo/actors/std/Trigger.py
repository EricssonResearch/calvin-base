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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class Trigger(Actor):
    """
    Pass on given _data_ every _tick_ seconds
    Outputs:
        data: given data
    """

    @manage(['tick', 'data', 'started'])
    def init(self, tick, data):
        self.tick = tick
        self.data = data
        self.timer = None
        self.started = False
        self.setup()

    def setup(self):
        self.use('calvinsys.events.timer', shorthand='timer')

    def start(self):
        self.timer = self['timer'].repeat(self.tick)
        self.started = True

    def will_migrate(self):
        if self.timer:
            self.timer.cancel()

    def did_migrate(self):
        self.setup()
        if self.started:
            self.start()

    @condition([], ['data'])
    @guard(lambda self: not self.started)
    def start_timer(self):
        self.start()
        return ActionResult(production=(self.data, ))

    @condition([], ['data'])
    @guard(lambda self: self.timer and self.timer.triggered)
    def trigger(self):
        self.timer.ack()
        return ActionResult(production=(self.data, ))

    action_priority = (start_timer, trigger)
    requires = ['calvinsys.events.timer']
