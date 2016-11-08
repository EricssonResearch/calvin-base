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

def init(replication_data):
    replication_data.replication_pressure_counts = {}
    replication_data.check_pressure_positions = {}
    replication_data.dereplication_position = 0
    replication_data.check_count = 0

def pre_check(node, **kwargs):
    """ Check if actor should scale out/in
    """
    # TODO check if scale in as well
    actor_id = kwargs['actor_id']
    actor = node.am.actors[actor_id]
    # Check limits
    if 'max' in kwargs and len(actor._replication_data.instances) > kwargs['max']:
        return PRE_CHECK.SCALE_IN
    if 'min' in kwargs and len(actor._replication_data.instances) < kwargs['min']:
        return PRE_CHECK.SCALE_OUT
    # Check performance
    replicate_actor = False
    dereplicate_actor = False
    same_count = True
    pressure = actor.get_pressure()
    counts = {}
    positions = {}
    for port_pair, port_queues in pressure.items():
        position, count, full_positions = port_queues
        counts[port_pair] = count
        positions[port_pair] = position
        if len(full_positions) < 2:
            continue
        # Check if two new recent queue full events
        if (actor._replication_data.replication_pressure_counts.get(port_pair, 0) < (count - 2) and
            full_positions[-1] > (position - 15) and
            full_positions[-2] > (position - 15)):
            replicate_actor = True
        # Check if long since a queue full event
        if (actor._replication_data.dereplication_position < (position - 40) and
            full_positions[-1] < (position - 40)):
            dereplicate_actor = True
        # Check if nothing has happened
        if actor._replication_data.check_pressure_positions.get(port_pair, 0) != position:
            same_count = False
    if same_count:
        actor._replication_data.check_count += 1
    else:
        actor._replication_data.check_count = 0
        actor._replication_data.check_pressure_positions = positions
    # Nothing has happend for a while, dereplicate
    if actor._replication_data.check_count > 5:
        dereplicate_actor = True
    if replicate_actor:
        if 'max' in kwargs and len(actor._replication_data.instances) == kwargs['max']:
            actor._replication_data.check_count = 0
            return PRE_CHECK.NO_OPERATION
        actor._replication_data.replication_pressure_counts = counts
        actor._replication_data.dereplication_position = position
        actor._replication_data.check_count = 0
        return PRE_CHECK.SCALE_OUT
    elif dereplicate_actor:
        if len(actor._replication_data.instances) == kwargs.get('min', 1):
            actor._replication_data.check_count = 0
            return PRE_CHECK.NO_OPERATION
        actor._replication_data.replication_pressure_counts = counts
        actor._replication_data.dereplication_position = position
        actor._replication_data.check_count = 0
        return PRE_CHECK.SCALE_IN
    else:
        return PRE_CHECK.NO_OPERATION

def initiate(node, actor, **kwargs):
    pass

def select(node, actor, **kwargs):
    if not actor._possible_placements:
        return []
    prefered_placements = actor._possible_placements - set(actor._collect_current_placement + [node.id])
    if not prefered_placements and not kwargs.get('alone', False):
        prefered_placements = actor._possible_placements
    if not prefered_placements:
        # When require being alone on runtime, we should fail here
        return None
    # TODO pick a runtime that is lightly loaded
    return [random.choice(list(prefered_placements))]