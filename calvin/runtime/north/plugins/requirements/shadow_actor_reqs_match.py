# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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

from calvin.utilities.calvin_callback import CalvinCB

def _requires_cb(key, value, counter, capabilities, descriptions, cb, actor_id, component):
    counter[0] -= 1
    if value is not None:
        capabilities[key] = value
    if counter[0] > 0:
        # Waiting for more responses
        return
    # We got all responses, distill the possible nodes for each actor type
    for d in descriptions:
        d['node_match'] = set.intersection(*[set(capabilities[r]) for r in d['requires']])

    # Pick first actor type that has any possible nodes
    for d in descriptions:
        if d['node_match']:
            cb(d['node_match'])
            return

    # Return empty list since no placement possible
    cb([])

def _description_cb(key, value, counter, descriptions, cb, node, shadow_params, actor_id, component):
    counter[0] -= 1
    if value is not None:
        mandatory = value['args']['mandatory']
        optional = value['args']['optional']
        # To be valid actor type all mandatory params need to be supplied and only valid params
        if all([p in shadow_params for p in mandatory]) and all([p in (mandatory + optional) for p in shadow_params]):
            descriptions.append(value)
    if counter[0] > 0:
        # Waiting for more responses
        return
    # We got all responses
    if len(descriptions) == 0:
        # Return a None when not affecting the placement
        cb(None)
        return

    # Now get all nodes with these capabilities
    requirements = set([r for d in descriptions for r in d['requires']])
    l = [len(requirements)]
    capabilities = {}
    for r in requirements:
        node.storage.get_index(['node', 'capabilities', r], cb=CalvinCB(_requires_cb,
                                                                            descriptions=descriptions,
                                                                            counter=l,
                                                                            capabilities=capabilities,
                                                                            actor_id=actor_id, 
                                                                            component=component,
                                                                            cb=cb))
    if not requirements:
        cb(None)

def _signature_cb(key, value, cb, node, shadow_params, actor_id, component):
    if value is None or len(value) == 0:
        # Return a None when not affecting the placement
        cb(None)
        return
    # We now have a list of actor type identifications
    l=[len(value)]
    descriptions = []
    for a in value:
        # Lookup actor type id to get description
        node.storage.get('actor_type-', a, CalvinCB(_description_cb,
                                                    counter=l,
                                                    descriptions=descriptions,
                                                    shadow_params=shadow_params,
                                                    node=node,
                                                    actor_id=actor_id,
                                                    cb=cb,
                                                    component=component))

def req_op(node, cb, signature, shadow_params, actor_id=None, component=None):
    """ Based on signature find actors' requires in global storage,
        filter actors based on params that are supplied
        and find any nodes with those capabilities
    """
    # Lookup signature to get a list of ids of the actor types
    node.storage.get_index(['actor', 'signature', signature], CalvinCB(_signature_cb,
                                                                       node=node,
                                                                       shadow_params=shadow_params,
                                                                       actor_id=actor_id,
                                                                       cb=cb,
                                                                       component=component))
