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


class DelayToken(Actor):
    """
    Sends input on after a given delay has passed. NOTE: Migration will currently reset timers.

    Input :
        token : anything
    Outputs:
        token : anything
    """

    @manage(['delay', 'timers'])
    def init(self, delay):
        self.delay = delay
        self.timers = []
        self.setup()

    def setup(self):
        for token in self.timers: 
            token['timer'] = self._new_timer()

    def _new_timer(self):
        timer = calvinsys.open(self, "sys.timer.once")
        calvinsys.write(timer, self.delay)
        return timer
        
    def will_migrate(self):
        for tokens in self.timers:
            calvinsys.close(tokens['timer'])
            tokens['timer'] = None

    def did_migrate(self):
        self.setup()

    @condition(['token'])
    def token_available(self, token):
        self.timers.append({'token': token, 'timer': self._new_timer()})
        

    @stateguard(lambda self: len(self.timers) > 0 and calvinsys.can_read(self.timers[0]['timer']))
    @condition([], ['token'])
    def timeout(self):
        item = self.timers.pop(0)
        calvinsys.read(item['timer'])
        return (item['token'], )

    action_priority = (timeout, token_available)
    requires = ['sys.timer.once']
