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
leader_election = "registry_central"

def init(replication_data):
    replication_data.known_runtimes = set([])
    replication_data.check_count = 0
    replication_data.limit_count = 10
    replication_data._terminate_with_node = False
    replication_data._one_per_runtime = False
    replication_data._measure_pressure = False
    replication_data.leader_election = leader_election
    replication_data.operation = PRE_CHECK.NO_OPERATION
    replication_data.selected_node_id = None

def set_state(replication_data, state):
    init(replication_data)
    replication_data.operation = state['operation']
    replication_data.selected_node_id = state['selected_node_id']

def get_state(replication_data):
    return {'operation': replication_data.operation, 'selected_node_id': replication_data.selected_node_id}

def pre_check(node, **kwargs):
    """ Check if actor should scale out/in
    """
    # TODO check if scale in as well
    data = kwargs['replication_data']
    # Check limits
    data.check_count += 1
    op = data.operation
    _log.debug("MANUAL REPLICATION OP %s" % PRE_CHECK.reverse_mapping[op])
    data.operation = PRE_CHECK.NO_OPERATION
    if op == PRE_CHECK.SCALE_OUT:
        data._sni = data.selected_node_id
    return op

def initiate(node, replication_data, **kwargs):
    pass

def select(node, replication_data, possible_placements, **kwargs):
    if not possible_placements:
        return []
    if replication_data.selected_node_id is not None and replication_data._sni in possible_placements:
        prefered_placements = set([replication_data.selected_node_id])
    else:
        prefered_placements = possible_placements
    replication_data.known_runtimes = prefered_placements
    if not prefered_placements:
        replication_data.limit_count = min(replication_data.limit_count + 10, 100)
        return None
    else:
        replication_data.limit_count = 10
    # TODO Send out all
    return [random.choice(list(prefered_placements))]

def direct_replication(node, replication_data, **kwargs):
    return False