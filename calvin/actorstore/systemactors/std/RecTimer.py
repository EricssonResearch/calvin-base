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


class RecTimer(Actor):
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
        self.setup()

    def setup(self):
        self.use('calvinsys.events.timer', shorthand='timer')
        self.timer = self['timer'].repeat(self.delay)

    def will_migrate(self):
        self.timer.cancel()

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self.timer and self.timer.triggered)
    @condition(['token'], ['token'])
    def flush(self, input):
        return (input, )

    @stateguard(lambda self: self.timer and self.timer.triggered)
    @condition()
    def clear(self):
        self.timer.ack()


    action_priority = (flush, clear)
    requires = ['calvinsys.events.timer']

    test_args = [1]

    # Trigger a timer then add tokens. The tokens shall wait for the next trigger.
    test_set = [
        {
            'setup': [lambda self: self.timer.trigger()],
            'in': {'token': []}, 'out': {'token': []}
        }
    ]

    # Add tokens, nothing returned since timer not triggered above shall have cleared.
    test_set += [
        {'in': {'token': [r]}, 'out': {'token': []}} for r in range(3)
    ]

    # Trigger the timer once then fetch three tokens.
    # All tokens shall be flushed.
    test_set += [
        {
            'setup': [lambda self: self.timer.trigger()],
            'in': {'token': []}, 'out': {'token': [0]}
        },
        {'in': {'token': []}, 'out': {'token': [1]}},
        {'in': {'token': []}, 'out': {'token': [2]}}
    ]
