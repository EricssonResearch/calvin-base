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

from calvin.runtime.south.plugins.io.sensors.distance import distance


class Distance(object):

    """
    Distance sensor
    """

    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        self._distance = distance.Distance(node, actor, self._new_measurement)
        self._has_data = False

    def _new_measurement(self, measurement):
        self._measurement = measurement
        self._has_data = True
        self._node.sched.trigger_loop(actor_ids=[self._actor])

    def start(self, period):
        self._distance.start(period)

    def stop(self):
        self._distance.stop()

    def has_data(self):
        return self._has_data

    def read(self):
        if self._has_data:
            self._has_data = False
            return self._measurement

def register(node=None, actor=None):
    return Distance(node, actor)
