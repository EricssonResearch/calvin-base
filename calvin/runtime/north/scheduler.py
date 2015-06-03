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

import sys
from infi.traceback import format_exception, traceback_context

from calvin.actor.actor import ActionResult
from calvin.runtime.south.plugins.async import async
import time
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Scheduler(object):

    """docstring for Scheduler"""

    def __init__(self, node, actor_mgr, monitor):
        super(Scheduler, self).__init__()
        self.actor_mgr = actor_mgr
        self.idle = False
        self.done = False
        self.node = node
        self.monitor = monitor
        self.delayed_loop = None

    def run(self):
        self.delayed_loop = None
        async.DelayedCall(0, self.loop_once)
        async.run_ioloop()

    def stop(self):
        self.done = True
        async.stop_ioloop()

    def loop_once(self):
        activity = self.monitor.loop(self)
        activity = self.fire_actors() or activity
        self.node.control.handle_request()

        _log.debug("SCHED: LOOP_ONCE %s (%s)" % (time.time(), "*" if activity else ""))
        if activity:
            # Something happened - run again
            self.delayed_loop = None
            async.DelayedCall(0, self.loop_once)
        else:
            # No firings, wait a while until next loop
            self.delayed_loop = async.DelayedCall(0.1, self.loop_once)

    def trigger_loop(self, delay=None):
        """ Trigger the loop_once potentially after waiting delay seconds """
        if delay is not None:
            # FIXME sets the triggers individually, but should have a granularity grouping
            async.DelayedCall(delay, self.trigger_loop)
            return
        if self.delayed_loop is not None:
            self.delayed_loop.cancel()
            self.delayed_loop = None
            async.DelayedCall(0, self.loop_once)
            _log.debug("SCHED: TRIGGERED %s" % time.time())

    def fire_actors(self):
        total = ActionResult(did_fire=False)
        with traceback_context():        
            for actor in self.actor_mgr.enabled_actors():
                try:
                    action_result = actor.fire()
                    total.merge(action_result)
                except:
                    _log.error('\n'.join(format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)))
        self.idle = not total.did_fire
