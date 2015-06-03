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

from calvin.runtime.south.plugins.async import async

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class TimerEvent(async.DelayedCall):
    def __init__(self, delay, trigger_loop, repeats=False):
        super(TimerEvent, self).__init__(delay, callback=self.trigger)
        self._triggered = False
        self.trigger_loop = trigger_loop
        self.repeats = repeats
        self.reset()

    @property
    def triggered(self):
        return self._triggered

    def ack(self):
        self._triggered = False

    def trigger(self):
        self._triggered = True
        if self.repeats:
            self.reset()
        self.trigger_loop()


class TimerHandler(object):
    def __init__(self, node):
        super(TimerHandler, self).__init__()
        self.node = node

    def once(self, delay):
        return TimerEvent(delay, self.node.sched.trigger_loop)

    def repeat(self, delay):
        return TimerEvent(delay, self.node.sched.trigger_loop, repeats=True)
        
    def _trigger_loop(self):
        return self.node.sched.trigger_loop()

def register(node, events):
    """
        Registers is called when the Event-system object is created.
        Place an object in the event object - in this case the
        nodes only timer object.

        Also register any hooks for actor migration.
    """

    events.timer = TimerHandler(node)
