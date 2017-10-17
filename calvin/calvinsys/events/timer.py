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
    def __init__(self, actor_id, delay, schedule_calvinsys, repeats=False):
        super(TimerEvent, self).__init__(delay, dc_callback=self.trigger)
        self._actor_id = actor_id
        self._triggered = False
        self.schedule_calvinsys = schedule_calvinsys
        self.repeats = repeats
        _log.debug("Set calvinsys timer %f %s on %s" % (delay, "repeat" if self.repeats else "", self._actor_id))

    @property
    def triggered(self):
        return self._triggered

    def ack(self):
        self._triggered = False

    def trigger(self):
        _log.debug("Trigger calvinsys timer on %s" % (self._actor_id))
        self._triggered = True
        if self.repeats:
            self.reset()
        self.schedule_calvinsys(actor_id=self._actor_id)


class TimerHandler(object):
    def __init__(self, node, actor):
        super(TimerHandler, self).__init__()
        self._actor = actor
        self.node = node

    def once(self, delay):
        return TimerEvent(self._actor.id, delay, self.node.sched.schedule_calvinsys)

    def repeat(self, delay):
        return TimerEvent(self._actor.id, delay, self.node.sched.schedule_calvinsys, repeats=True)

def register(node, actor, events=None):
    """
        Registers is called when the Event-system object is created.
        Place an object in the event object - in this case the
        nodes only timer object.

        Also register any hooks for actor migration.
        @TODO: Handle migration (automagically and otherwise.)
    """

    return TimerHandler(node=node, actor=actor)
