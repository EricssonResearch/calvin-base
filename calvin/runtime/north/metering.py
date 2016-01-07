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


class Metering(object):
    """Metering logs all actor activity"""
    def __init__(self, node):
        super(Metering, self).__init__()
        self.node = node
        self.timeout = _conf.get(None, 'metering_timeout')
        self.actors_log = {}
        self.actors_meta = {}
        self.active = False
        self.users = {}
        self.oldest = time.time()

    def fired(self, actor_id, action_name):
        if self.active:
            t = time.time()
            self.actors_log[actor_id].append((t, action_name))
            if self.oldest < t - self.timeout:
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

    def forget(self, current):
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

    def add_actor_info(self, actor):
        self.actors_meta[actor.id] = {}
        self.actors_log[actor.id] = []
        for action_method in actor.__class__.action_priority:
            self.actors_meta[actor.id][action_method.__name__] = {
                    'inports': {p[0]: p[1] for p in action_method.action_input},
                    'outports': {p[0]: p[1] for p in action_method.action_output}}

    def get_actors_info(self, user_id):
        return self.actors_meta