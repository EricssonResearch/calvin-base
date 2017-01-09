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

req_type = "replication"

def init(replication_data):
    replication_data.known_runtimes = [None, None]
    replication_data.check_count = 0
    replication_data.limit_count = 10
    replication_data._terminate_with_node = True
    replication_data._one_per_runtime = True

def set_state(replication_data, state):
    init(replication_data)

def get_state(replication_data):
    return {}

def pre_check(node, **kwargs):
    """ Check if actor should scale out/in
    """
    # TODO check if scale in as well
    actor_id = kwargs['actor_id']
    actor = node.am.actors[actor_id]
    data = actor._replication_data
    # Check limits
    if 'max' in kwargs and len(data.instances) == kwargs['max']:
        return PRE_CHECK.NO_OPERATION
    if 'max' in kwargs and len(data.instances) > kwargs['max']:
        return PRE_CHECK.SCALE_IN
    if 'min' in kwargs and len(data.instances) < kwargs['min']:
        return PRE_CHECK.SCALE_OUT
    data.check_count += 1
    if len(data.known_runtimes) > 1 or data.check_count > data.limit_count:
        data.check_count = 0
        return PRE_CHECK.SCALE_OUT
    else:
        return PRE_CHECK.NO_OPERATION

def initiate(node, actor, **kwargs):
    pass

def select(node, actor, possible_placements, **kwargs):
    if not possible_placements:
        return []
    prefered_placements = possible_placements - set([node.id])
    actor._replication_data.known_runtimes = prefered_placements
    if not prefered_placements:
        actor._replication_data.limit_count = min(actor._replication_data.limit_count + 10, 100)
        return None
    else:
        actor._replication_data.limit_count = 10
    # TODO Send out all
    return [random.choice(list(prefered_placements))]