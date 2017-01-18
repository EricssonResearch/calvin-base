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


class Delay(Actor):
    """
    Pass input after a given delay
    Input :
        token : anything
    Outputs:
        token : anything
    """

    @manage(['delay'])
    def init(self, delay=0.1):
        self.delay = delay
        self.timers = []
        self.setup()

    def setup(self):
        self.use('calvinsys.events.timer', shorthand='timer')

    def will_migrate(self):
        raise Exception("std.Delay can not migrate!")

    def did_migrate(self):
        raise Exception("std.Delay can not migrate!")

    @condition(['token'])
    def tokenAvailable(self, input):
        self.timers.append({'token': input, 'timer': self['timer'].once(self.delay)})
        

    @stateguard(lambda self: len(self.timers) > 0 and self.timers[0]['timer'].triggered)
    @condition([], ['token'])
    def timeout(self):
        o = self.timers.pop(0)
        o['timer'].ack()
        return (o['token'], )

    action_priority = (timeout, tokenAvailable)
    requires = ['calvinsys.events.timer']

    test_args = [1]

    # Test that two tokens are consumed without any output
    test_set = [
        {
            'in': {'token': [r]},
            'out': {'token': []}
        } for r in range(3)
    ]

    # Trigger the timers one at a time and check that the previously inserted tokens
    # are genererated in order, one at a time.
    test_set += [
        {
            'setup': [lambda self: self.timers[0]['timer'].trigger()],
            'in': {'token': []},
            'out': {'token': [r]},
        } for r in range(3)
    ]
