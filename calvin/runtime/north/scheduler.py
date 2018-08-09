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
import logging

from monitor import Event_Monitor, VisualizingMonitor
from calvin.runtime.south.async import async
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig

_log = get_logger(__name__)
_conf = calvinconfig.get()

class BaseScheduler(object):

    """
    The scheduler is the only active component in a runtime,
    except for calvinsys and token transport. Every other piece of
    code is (or should be) purely reactive.

    This class cannot be used as a scheduler
    """

    def __init__(self, node, actor_mgr):
        super(BaseScheduler, self).__init__()
        self.node = node
        self.actor_mgr = actor_mgr
        self.done = False
        self._tasks = []
        self._scheduled = None
        # FIXME: later
        self._replication_interval = 2
        self._maintenance_delay = _conf.get(None, "maintenance_delay") or 300
        self._pressure_event_actor_ids = set([])

    # System entry point
    def run(self):
        self.insert_task(self._maintenance_loop, self._maintenance_delay)
        self.insert_task(self._check_replication, self._replication_interval)
        self.insert_task(self.strategy, 0)
        async.run_ioloop()

    # System exit point
    def stop(self):
        if not self.done:
            async.DelayedCall(0, async.stop_ioloop)
        self.done = True

    ######################################################################
    # Event "API" used by subsystems to inform scheduler about events
    # Most of them needs to be subclassed in a working scheduler
    ######################################################################

    def tunnel_rx(self, endpoint):
        """Token recieved on endpoint"""
        # We got a token, meaning that the corrsponding actor could possibly fire
        pass

    def tunnel_tx_ack(self, endpoint):
        """Token successfully sent on endpoint"""
        # We got back ACK on sent token; at least one slot free in out queue, endpoint can send again at any time
        pass

    def tunnel_tx_nack(self, endpoint):
        """Token unsuccessfully sent on endpoint"""
        # We got back NACK on sent token, endpoint should wait before resending
        pass

    def tunnel_tx_throttle(self, endpoint):
        """Backoff request for endpoint"""
        # Schedule tx for endpoint at this time
        # FIXME: Under what circumstances is this method called?
        pass

    def schedule_calvinsys(self, actor_id=None):
        """Incoming platform event"""
        pass

    def register_endpoint(self, endpoint):
        pass

    def unregister_endpoint(self, endpoint):
        pass

    def replication_direct(self, replication_id=None, delay=0):
        """ Schedule an (early) replication management for at least replication_id.
            Delay can be used for scaling that know when in future e.g. scaling-in
            should be evaluated.
        """
        # TODO make use of replication_id when we have that granularity in the scheduler
        self.insert_task(self._check_replication, delay)

    def trigger_pressure_event(self, actor_id=None):
        """ Schedule an pressure event for actor_id """
        _log.debug("trigger_pressure_event %s" % actor_id)
        self._pressure_event_actor_ids.add(actor_id)
        self.insert_task(self._check_pressure, 0)

    ######################################################################
    # Stuff that needs to be implemented in a subclass
    ######################################################################

    def strategy(self):
        """This is where the scheduling happens..."""
        raise Exception("Really need a strategy")

    def watchdog(self):
        """If nothing else is scheduled, this will be called after 60s"""
        pass

    ######################################################################
    # Semi-private stuff, should be cleaned up later
    ######################################################################

    #
    # Replication
    #
    def _check_replication(self):
        # Control replication
        self.node.rm.replication_loop()
        # Need to only insert task if none before replication interval, otherwise build up more and more tasks
        tt = time.time() + self._replication_interval
        if not any([t[0] < tt for t in self._tasks if t[1] == self._check_replication]):
            self.insert_task(self._check_replication, self._replication_interval)
        _log.debug("Next replication loop in %s %d %d" % (str([t[0] - time.time() for t in self._tasks if t[1] == self._check_replication]),
                    [t[1] == self._check_replication for t in self._tasks].index(True), len(self._tasks)))
        self.insert_task(self.strategy, 0)

    def _check_pressure(self):
        _log.debug("_check_pressure %s" % self._pressure_event_actor_ids)
        self.node.rm.check_pressure(self._pressure_event_actor_ids)
        self._pressure_event_actor_ids = set([])
        if not [True for t in self._tasks if t[1] == self._check_pressure]:
            self.insert_task(self._check_pressure, 30)

    #
    # Maintenance loop
    #
    def _maintenance_loop(self):
        # Migrate denied actors
        for actor in self.actor_mgr.migratable_actors():
            self.actor_mgr.migrate(actor.id, actor.migration_info["node_id"],
                                   callback=CalvinCB(actor.remove_migration_info))
        # Enable denied actors again if access is permitted. Will try to migrate if access still denied.
        for actor in self.actor_mgr.denied_actors():
            actor.enable_or_migrate()
        # TODO: try to migrate shadow actors as well.
        # Since we may have moved stuff around, schedule strategy
        self.insert_task(self.strategy, 0)
        # Schedule next maintenance
        self.insert_task(self._maintenance_loop, self._maintenance_delay)

    def trigger_maintenance_loop(self, delay=False):
        """Public API"""
        if delay:
            # No need to schedule delayed maintenance, we do that periodically anyway
            return
        self.insert_task(self._maintenance_loop, 0)

    ######################################################################
    # Quite-private stuff, fairly generic
    ######################################################################

    def insert_task(self, what, delay):
        """Call to insert a task"""
        # Insert a task in time order,
        # if it ends up first in list, re-schedule _process_next
        t = time.time() + delay
        # task is (time, func)
        task = (t, what)
        index = len(self._tasks)
        if index:
            for i, ti in enumerate(self._tasks):
                if ti[0] > t:
                    index = i
                    break
        # If list was empty => index = 0
        # If slot found => index is insertion point
        # If slot not found => index is length of list <=> append
        # coalesce => don't add a task b/c we already will do that
        coalesce = (index > 0 and delay == 0 and self._tasks[index-1][1] == what)
        if coalesce:
            return
        self._tasks.insert(index, task)
        # print "INSERTING TASK AT SLOT", index
        # print "TASKS:", [(t, f.__name__) for t, f in self._tasks]
        # If we're first, reschedule
        if index == 0:
            self._schedule_next(delay, self._process_next)

    # Don't call directly
    def _schedule_next(self, delay, what):
        if self._scheduled:
            self._scheduled.cancel()
        self._scheduled = async.DelayedCall(delay, what)

    # Don't call directly
    def _process_next(self):
        # Get next task from queue and do it unless next task is in the future,
        # in that case, schedule _process_next (this method) at that time
        _, todo = self._tasks.pop(0)
        todo()
        if self._tasks:
            t, _ = self._tasks[0]
            delay = max(0, t - time.time())
            self._schedule_next(delay, self._process_next)
        else:
            # Queue is empty, set a watchdog to go off in 60s
            self.insert_task(self.watchdog, 60)
        if not self._scheduled.active():
            raise Exception("NO SCHEDULED TASK!")

    ######################################################################
    # Default implementation of _fire_actors, and _fire_actor
    # Can be used, but should be cleaned up and/or overridden
    ######################################################################

    def _fire_actors(self, actors):
        """
        Try to fire actions on actors on this runtime.
        Parameter 'actors' is a set of actors to try (in that ).
        Returns a set with id of actors that did fire at least one action
        """
        did_fire_actor_ids = set()
        for actor in actors:
            try:
                _log.debug("Fire actor %s (%s, %s)" % (actor.name, actor._type, actor.id))
                did_fire_action = self._fire_actor(actor)
                if did_fire_action:
                    did_fire_actor_ids.add(actor.id)
            except Exception as e:
                _log.exception(e)

        return did_fire_actor_ids

    def _fire_actor(self, actor):
        """
        Try to fire actions on actor on this runtime.
        Returns boolean that is True if actor fired
        """
        #
        # First make sure we are allowed to run
        #
        if not actor._authorized():
            return False

        start_time = time.time()
        actor_did_fire = False
        #
        # Repeatedly go over the action priority list
        #
        done = False
        while not done:
            did_fire, output_ok, exhausted = actor.fire()
            actor_did_fire |= did_fire
            if did_fire:
                #
                # Limit time given to actors even if it could continue a new round of firing
                #
                time_spent = time.time() - start_time
                done = time_spent > 0.020
            else:
                #
                # We reached the end of the list without ANY firing during this round
                # => handle exhaustion and return
                #
                # FIXME: Move exhaust handling to scheduler
                actor._handle_exhaustion(exhausted, output_ok)
                done = True

        return actor_did_fire

    def _fire_actor_non_preemptive(self, actor):
        """
        Try to fire actions on actor on this runtime.
        Returns boolean that is True if actor fired
        """
        #
        # First make sure we are allowed to run
        #
        if not actor._authorized():
            return False

        #
        # Repeatedly go over the action priority list
        #
        done = False
        actor_did_fire = False
        while not done:
            did_fire, output_ok, exhausted = actor.fire()
            actor_did_fire |= did_fire
            if not did_fire:
                #
                # We reached the end of the list without ANY firing during this round
                # => handle exhaustion and return
                #
                # FIXME: Move exhaust handling to scheduler
                actor._handle_exhaustion(exhausted, output_ok)
                done = True

        return actor_did_fire


    def _fire_actor_once(self, actor):
        """
        Try to fire action on actor on this runtime.
        Returns boolean that is True if actor fired
        """
        #
        # First make sure we are allowed to run
        #
        if not actor._authorized():
            return False

        did_fire, output_ok, exhausted = actor.fire()
        if not did_fire:
            # => handle exhaustion and return
            #
            # FIXME: Move exhaust handling to scheduler
            actor._handle_exhaustion(exhausted, output_ok)

        return did_fire


######################################################################
# SIMPLE SCHEDULER
######################################################################
class SimpleScheduler(BaseScheduler):

    """A very naive example scheduler deriving from BaseScheduler"""

    def __init__(self, node, actor_mgr):
        super(SimpleScheduler, self).__init__(node, actor_mgr)
        monitor_class = VisualizingMonitor if _log.getEffectiveLevel() is logging.DEBUG else Event_Monitor
        _log.debug("monitor_class is {}".format(monitor_class.__name__))
        self.monitor = monitor_class()

    def tunnel_rx(self, endpoint):
        """Token recieved on endpoint"""
        # We got a token, meaning that the corrsponding actor could possibly fire
        self.insert_task(self.strategy, 0)

    def tunnel_tx_ack(self, endpoint):
        """Token successfully sent on endpoint"""
        # We got back ACK on sent token; at least one slot free in out queue, endpoint can send again at any time
        self.monitor.clear_backoff(endpoint)
        self.insert_task(self.strategy, 0)

    def tunnel_tx_nack(self, endpoint):
        """Token unsuccessfully sent on endpoint"""
        # We got back NACK on sent token, endpoint should wait before resending
        self.monitor.set_backoff(endpoint)
        next_slot = self.monitor.next_slot()
        if next_slot:
            current = time.time()
            self.insert_task(self.strategy, max(0, next_slot - current))

    def tunnel_tx_throttle(self, endpoint):
        """Backoff request for endpoint"""
        # Schedule tx for endpoint at this time
        pass
        # FIXME: Under what circumstances is this method called?

    def schedule_calvinsys(self, actor_id=None):
        """Incoming platform event"""
        self.insert_task(self.strategy, 0)

    def register_endpoint(self, endpoint):
        self.monitor.register_endpoint(endpoint)
        # Possibly after reconnect
        if endpoint.port.owner.enabled():
            self.insert_task(self.strategy, 0)

    def unregister_endpoint(self, endpoint):
        self.monitor.unregister_endpoint(endpoint)

    # There are at least five things that needs to be done:
    # 1. Call fire() on actors
    # 2. Call communicate on endpoints
    #    2.a Throttle comm if needed
    # 3. Call replication_loop every now and then (handled by base class)
    # 4. Call maintenance_loop every now and then (handled by base class)
    # 5. Implement watchdog as a final resort?

    def strategy(self):
        # Really naive -- always try everything
        list_of_endpoints = self.monitor.endpoints
        did_transfer_tokens = self.monitor.communicate(list_of_endpoints)
        actors_to_fire = self.actor_mgr.enabled_actors()
        did_fire_actor_ids = self._fire_actors(actors_to_fire)
        activity = did_transfer_tokens or bool(did_fire_actor_ids)
        if activity:
            self.insert_task(self.strategy, 0)

    def watchdog(self):
        # Log and try to get back on track....
        _log.warning("WATCHDOG TRIGGERED")
        self.insert_task(self.strategy, 0)

######################################################################
# ROUND-ROBIN SCHEDULER
######################################################################
class RoundRobinScheduler(SimpleScheduler):

    def strategy(self):
        # Communicate
        list_of_endpoints = self.monitor.endpoints
        did_transfer_tokens = self.monitor.communicate(list_of_endpoints)
        # Round Robin
        actors_to_fire = self.actor_mgr.enabled_actors()
        did_fire_actor_ids = [actor.id for actor in actors_to_fire if self._fire_actor_once(actor)]
        # Repeat if there was any activity
        activity = did_transfer_tokens or bool(did_fire_actor_ids)
        if activity:
            self.insert_task(self.strategy, 0)


######################################################################
# NON-PREEMPTIVE SCHEDULER
######################################################################
class NonPreemptiveScheduler(SimpleScheduler):

    def strategy(self):
        # Communicate
        list_of_endpoints = self.monitor.endpoints
        did_transfer_tokens = self.monitor.communicate(list_of_endpoints)
        # Non-preemptive
        actors_to_fire = self.actor_mgr.enabled_actors()
        did_fire_actor_ids = [actor.id for actor in actors_to_fire if self._fire_actor_non_preemptive(actor)]
        # Repeat if there was any activity
        activity = did_transfer_tokens or bool(did_fire_actor_ids)
        if activity:
            self.insert_task(self.strategy, 0)

