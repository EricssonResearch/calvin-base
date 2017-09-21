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


class RecTimer(Actor):
    """
    After first token, pass on token once every 'delay' seconds. *Deprecated*
    
    This actor is identical to ClassicDelay.
    
    Input :
        token: anything
    Outputs:
        token: anything
    """

    @manage(['timer', 'delay', 'started'])
    def init(self, delay):
        self.delay = delay
        self.timer = calvinsys.open(self, "sys.timer.repeating")
        self.started = False

    @stateguard(lambda self: not self.started)
    @condition(['token'], ['token'])
    def start_timer(self, token):
        self.started = True
        calvinsys.write(self.timer, self.delay)
        return (token, )

    @stateguard(lambda self: calvinsys.can_read(self.timer))
    @condition(['token'], ['token'])
    def passthrough(self, token):
        calvinsys.read(self.timer)
        return (token, )

    action_priority = (start_timer, passthrough)
    requires = ['sys.timer.repeating']
