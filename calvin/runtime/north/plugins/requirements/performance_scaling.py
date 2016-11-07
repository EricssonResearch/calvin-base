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

from calvin.runtime.north.replicationmanager import PRE_CHECK
import random

def pre_check(node, **kwargs):
    """ Check if actor should scale out/in
    """
    # TODO check if scale in as well
    actor_id = kwargs['actor_id']
    actor = node.am.actors[actor_id]
    # Check limits
    if 'max' in kwargs and len(actor._replication_data.instances) == kwargs['max']:
        return PRE_CHECK.NO_OPERATION
    if 'max' in kwargs and len(actor._replication_data.instances) > kwargs['max']:
        return PRE_CHECK.SCALE_IN
    if 'min' in kwargs and len(actor._replication_data.instances) < kwargs['min']:
        return PRE_CHECK.SCALE_OUT
    # Check performance
    replicate_actor = False
    pressure = actor.get_pressure()
    counts = {}
    for port_pair, port_queues in pressure.items():
        position, count, full_positions = port_queues
        counts[port_pair] = count
        if len(full_positions) < 2:
            continue
        # Check if two new recent queue full events
        if (actor._replication_data.replication_pressure_counts.get(port_pair, 0) < (count - 2) and
            full_positions[-1] > (position - 15) and
            full_positions[-2] > (position - 15)):
            replicate_actor = True
    if replicate_actor:
         actor._replication_data.replication_pressure_counts = counts
         return PRE_CHECK.SCALE_OUT
    else:
        return PRE_CHECK.NO_OPERATION

def initiate(node, actor, **kwargs):
    pass

def select(node, actor, **kwargs):
    if not actor._possible_placements:
        return []
    prefered_placements = actor._possible_placements - set(actor._collect_current_placement + [node.id])
    if not prefered_placements:
        prefered_placements = actor._possible_placements
    # TODO pick a runtime that is lightly loaded
    return [random.choice(list(prefered_placements))]