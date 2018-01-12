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

from calvin.utilities.replication_defs import PRE_CHECK
import random
import time
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

req_type = "replication"
leader_election = "actor"

def init(replication_data):
    replication_data.pressure = {}
    replication_data.dereplication_count = 1
    replication_data._pressure_event = 0
    replication_data.leader_election = leader_election
    replication_data._terminate_with_node = False
    replication_data._measure_pressure = True
    alone = replication_data.requirements['kwargs'].get('alone', False)
    replication_data._one_per_runtime = alone
    if alone:
        replication_data._placement_req = [{
                'op': 'replica_nodes',
                'kwargs': {'replication_id': replication_data.id},
                'type': '-'
            },{
                'op': 'actor_nodes',
                'kwargs': {},
                'type': '-'
            }]

def set_state(replication_data, state):
    init(replication_data)

def get_state(replication_data):
    state = {}
    return state

def pre_check(node, **kwargs):
    """ Check if actor should scale out/in
    """
    # TODO check if scale in as well
    replication_data = kwargs['replication_data']
    # Check limits
    if kwargs.get('max', None) == kwargs.get('min', None) and len(replication_data.instances) == kwargs.get('min', None):
        return PRE_CHECK.NO_OPERATION
    if 'max' in kwargs and len(replication_data.instances) > kwargs['max']:
        return PRE_CHECK.SCALE_IN
    if 'min' in kwargs and len(replication_data.instances) < kwargs['min']:
        return PRE_CHECK.SCALE_OUT
    if not replication_data.pressure:
        return PRE_CHECK.NO_OPERATION
    # Check performance
    replicate = False
    dereplicate = False
    t = time.time() + replication_data.pressure_event_diff
    for p in replication_data.pressure.values():
        if len(p['pressure']) < 2:
            continue
        if ((p['pressure'][-1][1] - p['pressure'][-2][1]) < 10 and
             p['pressure'][-1][1] > replication_data._pressure_event):
            # Less than 10 sec between queue full and not reported, maybe scale out
            replication_data._pressure_event = max(p['pressure'][-1][1], replication_data._pressure_event)
            replicate = True
            break
        if (p['pressure'][-1][1] < (t - 30 * replication_data.dereplication_count)):
            # More than 30 sec since queue full, scale in
            replication_data._pressure_event = max(p['pressure'][-1][1], replication_data._pressure_event)
            replication_data.dereplication_count += 1
            dereplicate = True
            node.sched.replication_direct(replication_data.id, 30)
            break
    if replicate:
        replication_data.dereplication_count = 1
        return PRE_CHECK.SCALE_OUT
    elif dereplicate:
        return PRE_CHECK.SCALE_IN
    else:
        return PRE_CHECK.NO_OPERATION

def initiate(node, actor, **kwargs):
    pass

def select(node, actor, possible_placements, **kwargs):
    if not possible_placements:
        return []
    # TODO pick a runtime that is lightly loaded
    return [random.choice(list(possible_placements))]

def direct_replication(node, replication_data, **kwargs):
    return False

def pressure_update(node, replication_data, pressure):
    t = time.time()
    replication_data.pressure_event_diff = pressure.pop('time', t) - t
    replication_data.pressure = pressure
    # Schedule a replication loop when a dereplication should be considered
    node.sched.replication_direct(replication_data.id, 30)
