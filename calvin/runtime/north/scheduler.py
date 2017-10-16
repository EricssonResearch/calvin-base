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
import time
import random

from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig

_log = get_logger(__name__)
_conf = calvinconfig.get()


class Scheduler(object):

    """docstring for Scheduler"""

    def __init__(self, node, actor_mgr, monitor):
        super(Scheduler, self).__init__()
        self.actor_mgr = actor_mgr
        self.done = False
        self.node = node
        self.monitor = monitor
        self._loop_once = None
        self._trigger_set = set()
        self._watchdog = None
        self._watchdog_timeout = 1
        self._maintenance_loop = None
        self._maintenance_delay = _conf.get(None, "maintenance_delay") or 300
        self.actor_pressures = {}

    def run(self):
        async.run_ioloop()

    def stop(self):
        if not self.done:
            async.DelayedCall(0, async.stop_ioloop)
        self.done = True

    def loop_once(self, fire_all=False):
        # We don't know how we got here, so cancel both of these (safe thing to do)
        self._cancel_watchdog()
        self._cancel_schedule()
            
        # Transfer tokens between actors
        activity = self.monitor.communicate(self)

        # Pick which set of actors to fire, None means EVERY actor
        actors_to_fire = None if fire_all else self._trigger_set
        did_fire, timeout, actor_ids = self.fire_actors(actors_to_fire)

        # Reset the set of potential actors
        self._trigger_set = set()

        # FIXME: This is probably not the correct way to compute activity
        activity = did_fire or activity or timeout
        
        if activity:
            # Something happened - run again
            self._schedule_actors(actor_ids=actor_ids)
        else:
            # No firings, set a watchdog timeout
            self._watchdog = async.DelayedCall(self._watchdog_timeout, self._watchdog_wakeup)


    def trigger_loop(self, actor_ids=None):
        if actor_ids is None:
            self._schedule_all()
        else:
            self._schedule_actors(actor_ids)

    def _cancel_schedule(self):
        if self._loop_once is not None:
            self._loop_once.cancel()
            self._loop_once = None
        
    def _cancel_watchdog(self):
        if self._watchdog is not None:
            self._watchdog.cancel()        
            self._watchdog = None
            
    def _watchdog_wakeup(self):
        _log.warning("Watchdog wakeup -- this should not really happen...")
        self._schedule_all()

    def _schedule_all(self):
        # If there is a scheduled loop_once then cancel it since it might be
        # scheduled later, and/or with argument set to False.
        self._cancel_watchdog()
        self._cancel_schedule()
        self._loop_once = async.DelayedCall(0, self.loop_once, True)

    def _schedule_actors(self, actor_ids):
        # Update the set of actors that could possibly fire
        self._trigger_set.update(actor_ids)
        # Schedule loop_once if-and-only-if
        #                    it is not already scheduled
        #                    AND
        #                    the set of actors is non-empty
        if self._loop_once is None and self._trigger_set:
            self._cancel_watchdog()
            self._loop_once = async.DelayedCall(0, self.loop_once)

    def schedule_tunnel(self, backoff_time=0):
        # If backoff_time > 0 don't call UNTIL that time has passed.
        # Doesn't work with current scheduler/monitor, so tunnel::communicate has a workaround
        self._cancel_watchdog()
        self._cancel_schedule()
        self._loop_once = async.DelayedCall(backoff_time, self.loop_once, True)
        

    def _log_exception_during_fire(self, e):
        _log.exception(e)

    def fire_actors(self, actor_ids=None):
        did_fire = False
        actor_ids = set()

        actors = self.actor_mgr.enabled_actors()
        # Shuffle order since now we stop after executing actors for too long
        random.shuffle(actors)

        for actor in actors:
            try:
                _log.debug("Fire actor %s (%s, %s)" % (actor.name, actor._type, actor.id))
                did_fire |= actor.fire()
                actor_ids.add(actor.id)
            except Exception as e:
                self._log_exception_during_fire(e)

        return (did_fire, False, actor_ids)

    def maintenance_loop(self):
        # Migrate denied actors
        for actor in self.actor_mgr.migratable_actors():
            self.actor_mgr.migrate(actor.id, actor.migration_info["node_id"],
                                   callback=CalvinCB(actor.remove_migration_info))
        # Enable denied actors again if access is permitted. Will try to migrate if access still denied.
        for actor in self.actor_mgr.denied_actors():
            actor.enable_or_migrate()
        # TODO: try to migrate shadow actors as well.
        self._maintenance_loop = None
        self.trigger_maintenance_loop(delay=True)

    def trigger_maintenance_loop(self, delay=False):
        # Never have more then one maintenance loop.
        if self._maintenance_loop is not None:
            self._maintenance_loop.cancel()
        if delay:
            self._maintenance_loop = async.DelayedCall(self._maintenance_delay, self.maintenance_loop)
        else:
            self._maintenance_loop = async.DelayedCall(0, self.maintenance_loop)


class DebugScheduler(Scheduler):
    """This is an instrumented version of the scheduler for use in debugging runs."""

    def __init__(self, node, actor_mgr, monitor):
        super(DebugScheduler, self).__init__(node, actor_mgr, monitor)

    def trigger_loop(self, actor_ids=None):
        #import inspect
        #import traceback
        super(DebugScheduler, self).trigger_loop(actor_ids=actor_ids)
        #(frame, filename, line_no, fname, lines, index) = inspect.getouterframes(inspect.currentframe())[1]
        #_log.debug("triggered %s by %s in file %s at %s" % (time.time(), fname, filename, line_no))
        #_log.debug("Trigger happend here:\n" + ''.join(traceback.format_stack()[-6:-1]))
        _log.analyze(self.node.id, "+ Triggered", None, tb=True)

    def schedule_tunnel(self, backoff_time=0):
        super(DebugScheduler, self).schedule_tunnel(backoff_time=backoff_time)

    def _log_exception_during_fire(self, e):
        from infi.traceback import format_exception
        _log.error('\n'.join(format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)))

    def fire_actors(self, actor_ids=None):
        from infi.traceback import traceback_context
        traceback_context()
        return super(DebugScheduler, self).fire_actors(actor_ids)
