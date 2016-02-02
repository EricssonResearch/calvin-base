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
from calvin.utilities import dynops
from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)

def get_description(out_iter, kwargs, final, signature):
    _log.debug("shadow_match:get_description BEGIN")
    if final[0]:
        _log.debug("shadow_match:get_description FINAL")
        out_iter.auto_final(kwargs['counter'])
    else:
        _log.debug("shadow_match:get_description ACT")
        kwargs['counter'] += 1
        kwargs['node'].storage.get_iter('actor_type-', signature, it=out_iter)
    _log.debug("shadow_match:get_description END")

def extract_capabilities(out_iter, kwargs, final, value):
    _log.debug("shadow_match:extract_capabilities BEGIN")
    shadow_params = kwargs.get('shadow_params', [])
    if not final[0] and value != dynops.FailedElement:
        _log.debug("shadow_match:extract_capabilities VALUE %s" % value)
        mandatory = value['args']['mandatory']
        optional = value['args']['optional'].keys()
        # To be valid actor type all mandatory params need to be supplied and only valid params
        if all([p in shadow_params for p in mandatory]) and all([p in (mandatory + optional) for p in shadow_params]):
            _log.debug("shadow_match:extract_capabilities ACT")
            kwargs['descriptions'].append(value)
            reqs = value['requires']
            new = set(reqs) - kwargs['capabilities']
            kwargs['capabilities'].update(new)
            out_iter.extend(new)
    if final[0]:
        _log.debug("shadow_match:extract_capabilities FINAL")
        out_iter.final()
    _log.debug("shadow_match:extract_capabilities END")


def get_capability(out_iter, kwargs, final, value):
    _log.debug("shadow_match:get_capability BEGIN")
    if final[0]:
        _log.debug("shadow_match:get_capability FINAL")
        out_iter.auto_final(kwargs['counter'])
    else:
        kwargs['counter'] += 1
        _log.debug("shadow_match:get_capability GET %s counter:%d" % (value, kwargs['counter']))
        out_iter.append(kwargs['node'].storage.get_index_iter(['node', 'capabilities', value], include_key=True))
    _log.debug("shadow_match:get_capability END")

def placement(out_iter, kwargs, final, capability_nodes):
    _log.debug("shadow_match:placement BEGIN %s" % (capability_nodes,))
    if final[0]:
        try:
            possible_nodes = set.union(*[d['node_match'] for d in kwargs['descriptions'] if 'node_match' in d])
        except:
            possible_nodes = set([])
            if not kwargs['capabilities']:
                # No capabilities required, then get final direct, ok
                out_iter.append(dynops.InfiniteElement())
                out_iter.final()
                return
        if not possible_nodes:
            # None found
            out_iter.final()
            return
        if any([isinstance(n, dynops.InfiniteElement) for n in possible_nodes]):
            # Some actor can have infinte placement, lets that be our response
            out_iter.append(dynops.InfiniteElement())
            out_iter.final()
            return
        # Send out the union of possible nodes
        out_iter.extend(possible_nodes)
        out_iter.final()
        return
    else:
        capability = "".join(capability_nodes[0].partition('calvinsys.')[1:])
        kwargs['capabilities'].setdefault(capability, []).append(capability_nodes[1])

    _log.debug("shadow_match:placement EVALUATE %s" % kwargs)
    # Update matches
    for d in kwargs['descriptions']:
        if 'node_match' not in d and not d['requires']:
            # No capability requirements
            _log.debug("shadow_match:placement No requires create Infinity")
            d['node_match'] = set([dynops.InfiniteElement()])
        elif set(d['requires']) <= set(kwargs['capabilities'].keys()):
            _log.debug("shadow_match:placement require:%s, caps:%s" % (d['requires'], kwargs['capabilities']))
            found = set.intersection(*[set(kwargs['capabilities'][r]) for r in d['requires']])
            new = found - d.setdefault('node_match', set([]))
            d['node_match'].update(new)
            # TODO drip out matches as they come, but how to handle infinte responses

def req_op(node, signature, shadow_params, actor_id=None, component=None):
    """ Based on signature find actors' requires in global storage,
        filter actors based on params that are supplied
        and find any nodes with those capabilities
    """
    # Lookup signature to get a list of ids of the actor types
    signature_iter = node.storage.get_index_iter(['actor', 'signature', signature])
    signature_iter.set_name("shadow_match:sign")
    # Lookup description for all matching actor types
    description_iter = dynops.Map(get_description, signature_iter, eager=True, counter=0, node=node)
    description_iter.set_name("shadow_match:desc")
    # Filter with matching parameters and return set of needed capabilities
    extract_caps_iter = dynops.Map(extract_capabilities, description_iter, eager=True, 
                                   shadow_params=shadow_params, capabilities=set([]), descriptions=[])
    extract_caps_iter.set_name("shadow_match:extract")
    # Lookup nodes having each capability
    get_caps_iter = dynops.Map(get_capability, extract_caps_iter, eager=True, counter=0, node=node)
    get_caps_iter.set_name("shadow_match:caps")
    # Previous returned iterable with iterables, chain them to one iterable
    collect_caps_iter = dynops.Chain(get_caps_iter)
    collect_caps_iter.set_name("shadow_match:collect")
    # return nodes that can host first seen actor type with all capabilities fulfilled
    placement_iter = dynops.Map(placement, collect_caps_iter, capabilities={}, 
                                descriptions=extract_caps_iter.get_kwargs()['descriptions'])
    placement_iter.set_name("shadow_match:place")
    return placement_iter