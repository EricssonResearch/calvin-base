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
        self.idle = False
        self.done = False
        self.node = node
        self.monitor = monitor
        self.delayed_loop = None
        self._loop_once = None
        self._trigger_set = set()
        self._heartbeat_loop = None
        self._heartbeat = 1
        self._maintenance_loop = None
        self._maintenance_delay = _conf.get(None, "maintenance_delay") or 300
        self.actor_pressures = {}

    def run(self):
        async.run_ioloop()

    def stop(self):
        if not self.done:
            async.DelayedCall(0, async.stop_ioloop)
        self.done = True

    def loop_once(self, all_=False):
        try:
            activity = self.monitor.loop(self)
        except:
            _log.exception("loop_once monitor failed")
            return

        actors_to_fire = None if all_ else self._trigger_set
        did_fire, timeout, actor_ids = self.fire_actors(actors_to_fire)

        self._loop_once = None

        local_trigger_set = self._trigger_set
        self._trigger_set = set()

        activity = did_fire or activity or timeout

        if activity:
            # Something happened - run again
            self.trigger_loop(0, actor_ids)
        else:
            # No firings, wait a while until next loop
            if self._heartbeat_loop is not None:
                self._heartbeat_loop.cancel()
            self._heartbeat_loop = async.DelayedCall(self._heartbeat, self.trigger_loop)

        # Control replication
        self.node.rm.replication_loop()

    def trigger_loop(self, delay=0, actor_ids=None):
        """ Trigger the loop_once potentially after waiting delay seconds """
        if delay > 0:
            _log.debug("Delayed trigger %s" % delay)
            async.DelayedCall(delay, self.loop_once, True)
        else:
            # Never have more then one outstanding loop_once
            if actor_ids is None:
                if self._loop_once is not None:
                    self._loop_once.cancel()
                self._loop_once = async.DelayedCall(0, self.loop_once, True)
            else:
                self._trigger_set.update(actor_ids)
                # Don't run None jobs
                if self._trigger_set == set([None]):
                    _log.debug("Ignoring fire")
                    return

                if self._loop_once is None:
                    self._loop_once = async.DelayedCall(0, self.loop_once)

    def _log_exception_during_fire(self, e):
        _log.exception(e)

    def fire_actors(self, actor_ids=None):
        did_fire = False
        actor_ids = set()

        actors = self.actor_mgr.enabled_actors()
        # Shuffle order since now we stop after executing actors for too long
        random.shuffle(actors)

        start_time = time.time()
        timeout = False
        for actor in actors:
            try:
                _log.debug("Fire actor %s (%s, %s)" % (actor.name, actor._type, actor.id))
                did_fire |= actor.fire()
                actor_ids.add(actor.id)
            except Exception as e:
                self._log_exception_during_fire(e)

            pressure = actor.get_pressure().values()
            pressure_values = [p for _, _, p in pressure]
            if self.actor_pressures.get(actor.id, False) != pressure_values:
                self.actor_pressures[actor.id] = pressure_values

            timeout = time.time() - start_time > 0.100
            if timeout:
                break

        # FIXME: self.idle = not (timeout or did_fire)
        self.idle = False if timeout else not did_fire

        return (did_fire, timeout, actor_ids)

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

    def trigger_loop(self, delay=0, actor_ids=None):
        #import inspect
        #import traceback
        super(DebugScheduler, self).trigger_loop(delay, actor_ids)
        #(frame, filename, line_no, fname, lines, index) = inspect.getouterframes(inspect.currentframe())[1]
        #_log.debug("triggered %s by %s in file %s at %s" % (time.time(), fname, filename, line_no))
        #_log.debug("Trigger happend here:\n" + ''.join(traceback.format_stack()[-6:-1]))
        _log.analyze(self.node.id, "+ Triggered", None, tb=True)

    def _log_exception_during_fire(self, e):
        from infi.traceback import format_exception
        _log.error('\n'.join(format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)))

    def fire_actors(self, actor_ids=None):
        from infi.traceback import traceback_context
        traceback_context()
        return super(DebugScheduler, self).fire_actors(actor_ids)
