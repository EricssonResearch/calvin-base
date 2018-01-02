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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys


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

    @manage(['timeout'])
    def init(self, timeout, immediate):
        self.timeout = timeout
        self.timer = None
        if immediate:
            self._start_timer()

    def _start_timer(self):
        if self.timer:
            calvinsys.close(self.timer)
        self.timer = calvinsys.open(self, "sys.timer.once", period=self.timeout)

    @stateguard(lambda actor: actor.timer and calvinsys.can_read(actor.timer))
    @condition([], ['timeout'])
    def timeout(self):
        _ = calvinsys.read(self.timer) # Ack (not strictly necessary since _start_timer will close timer)
        self._start_timer()
        return (True, )

    @condition(['data'], ['data'])
    def passthrough(self, data):
        # reset timeout
        self._start_timer()
        return (data, )

    action_priority = (timeout, passthrough)
    requires = ['sys.timer.once']


#    TBD: Reenable test after updating to use new calvinsys API
#    test_kwargs = {'timeout': 10, 'immediate': True}
#    test_set = [
#        {
#            'inports': {'data': ["data_to_forward"]},
#            'outports': {'data': ["data_to_forward"],
#                         'timeout': [False]}
#        }
#    ]

