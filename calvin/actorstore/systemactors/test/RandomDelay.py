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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys, calvinlib


class RandomDelay(Actor):
    """
    Sends input on after a random delay has passed.

    Input :
        token : anything
    Outputs:
        token : anything
    """

    @manage(['timers'])
    def init(self):
        self.timers = []

    def new_timer(self):
        timer = calvinsys.open(self, "sys.timer.once")
        rng = calvinlib.use("math.random")
        delay = rng.random_integer(lower=0, upper=2)
        calvinsys.write(timer, delay)
        return timer
        
    @condition(['token'])
    def token_available(self, token):
        self.timers.append({'token': token, 'timer': self.new_timer()})

    @stateguard(lambda self: len(self.timers) > 0 and calvinsys.can_read(self.timers[0]['timer']))
    @condition([], ['token'])
    def timeout(self):
        item = self.timers.pop(0)
        calvinsys.read(item['timer'])
        calvinsys.close(item['timer'])
        return (item['token'], )

    action_priority = (timeout, token_available)
    requires = ['sys.timer.once', 'math.random']
