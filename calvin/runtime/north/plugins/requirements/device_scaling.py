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
import sys

req_type = "replication"
leader_election = "registry_central"

def init(replication_data):
    replication_data.known_runtimes = set([])
    replication_data.check_count = 0
    replication_data.limit_count = 1
    replication_data._terminate_with_node = True
    replication_data._one_per_runtime = True
    replication_data._measure_pressure = False
    replication_data._placement_req = [{
                'op': 'replica_nodes',
                'kwargs': {'replication_id': replication_data.id},
                'type': '-'
            },{
                'op': 'actor_nodes',
                'kwargs': {},
                'type': '-'
            }]
    replication_data.leader_election = leader_election

def set_state(replication_data, state):
    init(replication_data)

def get_state(replication_data):
    return {}

def pre_check(node, replication_data, **kwargs):
    """ Check if actor should scale out/in
    """
    # Check limits
    if 'max' in kwargs and len(replication_data.instances) == kwargs['max']:
        return PRE_CHECK.NO_OPERATION
    if 'max' in kwargs and len(replication_data.instances) > kwargs['max']:
        return PRE_CHECK.SCALE_IN
    replication_data.check_count += 1
    if replication_data.known_runtimes:
        replication_data.check_count = 0
        return PRE_CHECK.SCALE_OUT_KNOWN
    elif replication_data.check_count > replication_data.limit_count:
        replication_data.check_count = 0
        return PRE_CHECK.SCALE_OUT
    else:
        return PRE_CHECK.NO_OPERATION

def initiate(node, replication_data, **kwargs):
    pass

def select(node, replication_data, possible_placements, **kwargs):
    if replication_data.known_runtimes and not possible_placements:
        # Called without new possible placements use known
        possible_placements = replication_data.known_runtimes
    if not possible_placements:
        replication_data.limit_count = min(replication_data.limit_count + 1, 10)
        return []
    else:
        replication_data.limit_count = 1
    replication_data.known_runtimes = possible_placements
    selected = random.choice(list(possible_placements))
    replication_data.known_runtimes -= set([selected])
    return [selected]

def direct_replication(node, replication_data, **kwargs):
    return bool(replication_data.known_runtimes) and len(replication_data.instances) < kwargs.get('max', sys.maxint)