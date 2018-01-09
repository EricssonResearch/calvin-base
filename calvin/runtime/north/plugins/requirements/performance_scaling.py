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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

req_type = "replication"
leader_election = "actor"

def init(replication_data):
    replication_data.replication_pressure_counts = {}
    replication_data.check_pressure_positions = {}
    replication_data.dereplication_position = {}
    replication_data.check_count = 0
    replication_data.leader_election = leader_election
    replication_data._terminate_with_node = False
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
    replication_data.replication_pressure_counts = state.get('replication_pressure_counts', {})
    replication_data.check_pressure_positions = state.get('check_pressure_positions', {})
    replication_data.dereplication_position =  state.get('dereplication_position', {})
    replication_data.check_count =  state.get('check_count', 0)

def get_state(replication_data):
    state = {}
    state['replication_pressure_counts'] = replication_data.replication_pressure_counts
    state['check_pressure_positions'] = replication_data.check_pressure_positions
    state['dereplication_position'] = replication_data.dereplication_position
    state['check_count'] = replication_data.check_count
    return state

def pre_check(node, **kwargs):
    """ Check if actor should scale out/in
    """
    # TODO check if scale in as well
    replication_data = kwargs['replication_data']
    replication_data._one_per_runtime = kwargs.get('alone', False)
    # Check limits
    if 'max' in kwargs and len(replication_data.instances) > kwargs['max']:
        return PRE_CHECK.SCALE_IN
    if 'min' in kwargs and len(replication_data.instances) < kwargs['min']:
        return PRE_CHECK.SCALE_OUT
    # Check performance
    replicate_actor = False
    dereplicate_actor = False
    same_count = True
    pressure = actor.get_pressure()
    counts = {pp: port_queues[1] for pp, port_queues in pressure.items()}
    positions = {pp: port_queues[0] for pp, port_queues in pressure.items()}
    full_positions = {pp: port_queues[2][-2:] for pp, port_queues in pressure.items() if len(port_queues[2]) >= 2}
    replicate_actor_pp = [
        replication_data.replication_pressure_counts.get(pp, 0) < (counts[pp] - 2) and
        fp[0] > (positions[pp] - 15) and fp[1] > (positions[pp] - 15)
        for pp, fp in full_positions.items()]
    limit = 60
    dereplicate_actor_pp = [
        replication_data.dereplication_position.get(pp, positions[pp]) < (positions[pp] - limit) and
        fp[1] < (positions[pp] - limit)
        for pp, fp in full_positions.items()]
    same_count_pp = [
        replication_data.check_pressure_positions.get(pp, 0) == positions[pp]
        for pp in full_positions]
    replicate_actor = any(replicate_actor_pp)
    dereplicate_actor = all(dereplicate_actor_pp)
    same_count = all(same_count_pp)
    #_log.info("PERF %s %s %s" % (positions.values(), counts.values(), full_positions.values()))
    #_log.info("REP %s" % ["Y" if r else "N" for r in replicate_actor_pp])
    #_log.info("DER %s" % ["Y" if r else "N" for r in dereplicate_actor_pp])
    #_log.info("SAM %s" % ["Y" if r else "N" for r in same_count_pp])
    if same_count:
        replication_data.check_count += 1
    else:
        replication_data.check_count = 0
        replication_data.check_pressure_positions = positions
    # Nothing has happend for a while, dereplicate
    if replication_data.check_count > 5:
        dereplicate_actor = True
    if replicate_actor:
        if 'max' in kwargs and len(replication_data.instances) == kwargs['max']:
            replication_data.check_count = 0
            return PRE_CHECK.NO_OPERATION
        replication_data.replication_pressure_counts = counts
        replication_data.dereplication_position = positions
        replication_data.check_count = 0
        return PRE_CHECK.SCALE_OUT
    elif dereplicate_actor:
        if len(replication_data.instances) == kwargs.get('min', 1):
            replication_data.check_count = 0
            return PRE_CHECK.NO_OPERATION
        replication_data.replication_pressure_counts = counts
        replication_data.dereplication_position = positions
        replication_data.check_count = 0
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