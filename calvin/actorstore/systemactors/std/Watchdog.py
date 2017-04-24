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

from calvin.actor.actor import Actor, manage, condition, stateguard


class Watchdog(Actor):
    """
    Data on inport is passed on to outport unchanged. If nothing has arrived on the inport after `timeout` seconds, then true is sent on the timeout port.
    If parameter `immediate` is false, then the timer will not start until at least one token has arrived, otherwise it will start upon instantiation.
    
    Inputs:
        data : anything
    Outputs:
        data: whatever arrived on the inport of the same name
        timeout: true iff timeout seconds has passed without tokens on inport
    """

    @manage(['timeout', 'immediate'])
    def init(self, timeout, immediate):
        self.timeout = timeout
        self.immediate = immediate
        self.timer = None
        self.started = False
        self.setup()

    def setup(self):
        self.use('calvinsys.events.timer', shorthand='timer')
        if self.immediate :
            self.start()

    def start(self):
        self.timer = self['timer'].once(self.timeout)
        self.started = True

    def will_migrate(self):
        if self.timer:
            self.timer.cancel()

    def did_migrate(self):
        self.setup()
        if self.started:
            self.start()

    @stateguard(lambda actor: not actor.started)
    @condition([], [])
    def start_timer(self):
        self.start()
        return ()

    @condition(['data'], ['data'])
    def passthrough(self, data):
        self.timer.cancel()
        # reset timeout
        self.timer = self['timer'].once(self.timeout)
        return (data, )

    @stateguard(lambda actor: actor.timer and actor.timer.triggered)
    @condition([], ['timeout'])
    def timeout(self):
        self.timer.ack()
        self.timer = self['timer'].once(self.timeout)
        return (True, )

    action_priority = (start_timer, passthrough, timeout)
    requires = ['calvinsys.events.timer']
