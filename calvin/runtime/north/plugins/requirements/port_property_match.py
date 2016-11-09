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

from calvin.utilities import dynops

req_type = "placement"

def req_op(node, port_property, actor_id=None, component=None):
    """ Lockup port_property returns a dynamic iterable which is a union of all possible runtimes 
        actor_id is the actor that this is requested for
        component contains a list of all actor_ids of the component if the actor belongs to a component else None
    """
    it = []
    for p in port_property:
        it.append(node.storage.get_index_iter(['node', 'capabilities', p]))
    if len(it) > 1:
        final = dynops.Union(*it)
    elif len(it) == 1:
        final = it[0]
    else:
        # Empty list, this is bad, but somone elses problem
        final = dynops.List()
        final.final()
    final.set_name("port_property_match")
    return final
