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
from calvin.utilities.attribute_resolver import format_index_string
# A cache of attribute lockups for actors in components
_cache={}

def _req_op_cb(key, value, cb, cache_key, actor_id, component):
    if cache_key:
        _cache[cache_key] = (_cache[cache_key][0], True, value)
        for c in _cache[cache_key][0].values():
            c(value if value else None)
        if len(_cache[cache_key][0]) == len(component):
            # Done then clean cache
            _cache.pop(cache_key) 
    else:
        cb(value if value else None)

def req_op(node, cb, index, actor_id=None, component=None):
    """ Lockup index if found callback cb is called with the node ids else None
        actor_id is the actor that this is requested for
        component contains a list of all actor_ids of the component if the actor belongs to a component else None
    """
    index_str = format_index_string(index)
    # Utilize a cache of the storage response for components
    # This is mainly to illustrate how to utilize the component and actor_id params for rules where this is needed
    if component:
        cache_key = (index_str, tuple(component))
        if cache_key in _cache:
            # Add in our callback
            _cache[cache_key][0][actor_id] = cb
            if _cache[cache_key][1]:
                # Already got value call cb directly
                value = _cache[cache_key][2]
                cb(value if value else None)
                if len(_cache[cache_key][0]) == len(component):
                    # Done then clean cache
                    _cache.pop(cache_key) 
            return
        else:
            _cache[cache_key] = ({actor_id:cb}, False, None)
    else:
        cache_key = None

    node.storage.get_index(index_str, CalvinCB(_req_op_cb, cache_key=cache_key,
                                                                actor_id=actor_id, cb=cb, component=component))
