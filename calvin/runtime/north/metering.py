# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

import time
from calvin.utilities import calvinlogger
from calvin.utilities import calvinuuid
from calvin.utilities import calvinconfig

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)

_metering = None

def get_metering():
    """ Returns the Metering singleton
    """
    global _metering
    return _metering


def set_metering(metering):
    """ Returns the Metering singleton
    """
    global _metering
    if _metering is None:
        _metering = metering
    return _metering

class Metering(object):
    """Metering logs all actor activity"""
    def __init__(self, node):
        super(Metering, self).__init__()
        self.node = node
        self.timeout = _conf.get(None, 'metering_timeout')
        self.aggregated_timeout = _conf.get(None, 'metering_aggregated_timeout')
        self.actors_log = {}
        self.actors_meta = {}
        self.actors_destroyed = {}
        self.active = False
        # Keep track of user's last access time, should inactive users be deleted? When?
        self.users = {}
        self.oldest = time.time()
        self.last_forget = time.time()
        self.next_forget_aggregated = time.time()
        self.actors_aggregated = {}
        self.actors_aggregated_time = {}

    def fired(self, actor_id, action_name):
        t = time.time()
        if self.aggregated_timeout > 0.0:
            # Aggregate
            self.actors_aggregated.setdefault(actor_id,
                                            {action: 0 for action in self.actors_meta[actor_id]})[action_name] += 1
            # Set [start time, modification time] and update modification time
            self.actors_aggregated_time.setdefault(actor_id, [t, t])[1] = t
            if self.next_forget_aggregated <= t:
                self.forget_aggregated(t)
        if self.active and self.timeout > 0.0:
            # Timed metering
            self.actors_log[actor_id].append((t, action_name))
            # Remove old data at most once per second
            if self.oldest < t - self.timeout and self.last_forget < t - 1.0:
                self.forget(t)

    def register(self, user_id=None):
        if not user_id:
            user_id = calvinuuid.uuid("METERING")
        if user_id in self.users:
            raise Exception("User id already in use")
        self.users[user_id] = time.time()
        self.active = True
        return user_id

    def unregister(self, user_id):
        if user_id in self.users:
            self.users.pop(user_id)
            self.active = bool(self.users)
            self.forget(time.time())
        else:
            raise Exception("User id not found")

    def get_timed_meter(self, user_id):
        if user_id not in self.users:
            _log.debug("get_timed_meter: User id not found")
            raise Exception("User id not found")
        t = time.time()
        response = {actor_id: [d for d in data if d[0] > self.users[user_id]] 
                                for actor_id, data in self.actors_log.iteritems()}
        self.users[user_id] = t
        self.forget(t)
        return response

    def get_aggregated_meter(self, user_id):
        if user_id not in self.users:
            _log.debug("get_aggregated_meter: User id not found")
            raise Exception("User id not found")
        response = {'activity': self.actors_aggregated, 'time': self.actors_aggregated_time}
        return response

    def forget(self, current):
        self.last_forget = current
        if not self.active:
            self.actors_log = {}
            self.oldest = current
            return
        t = min(self.users.values())
        if t < current - self.timeout:
            t = current - self.timeout
        self.oldest = t
        for actor_id, data in self.actors_log.iteritems():
            self.actors_log[actor_id] = [d for d in data if d[0] > t]

    def forget_aggregated(self, current):
        # Remove meta info that we don't have any action data for anyway.
        # Also remove aggregated data for timeouted destroyed actors
        et = current - (self.timeout * 2) - self.aggregated_timeout
        for actor_id, dt in self.actors_destroyed.iteritems():
            if dt < et:
                self.actors_meta.pop(actor_id)
                try:
                    self.actors_aggregated_time.pop(actor_id)
                    self.actors_aggregated.pop(actor_id)
                except:
                    pass
        self.actors_destroyed = {actor_id: dt for actor_id, dt in self.actors_destroyed.iteritems() if dt >= et}
        if self.actors_destroyed:
            self.next_forget_aggregated = (min(self.actors_destroyed.values()) +
                                           self.aggregated_timeout + (self.timeout * 2))
        else:
            self.next_forget_aggregated = current + self.aggregated_timeout + (self.timeout * 2)

    def add_actor_info(self, actor):
        self.actors_meta[actor.id] = {}
        # Remove note on actor destroyed for an actor that migrates back
        if actor.id in self.actors_destroyed:
            self.actors_destroyed.pop(actor.id)
        # Make sure the log exist but don't overwrite old data for an actor that migrates back
        self.actors_log.setdefault(actor.id, [])
        for action_method in actor.__class__.action_priority:
            self.actors_meta[actor.id][action_method.__name__] = {
                    'inports': {p[0]: p[1] for p in action_method.action_input},
                    'outports': {p[0]: p[1] for p in action_method.action_output}}
        _log.analyze(self.node.id, "+", {'actor_id': actor.id, 'metainfo': self.actors_meta[actor.id]})

    def remove_actor_info(self, actor_id):
        if actor_id in self.actors_meta:
            self.actors_destroyed[actor_id] = time.time()
            self.next_forget_aggregated = (min(self.actors_destroyed.values()) +
                                           self.aggregated_timeout + (self.timeout * 2))

    def get_actors_info(self, user_id):
        return self.actors_meta