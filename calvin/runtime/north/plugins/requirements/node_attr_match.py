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
from calvin.utilities import dynops

req_type = "placement"

def req_op(node, index, actor_id=None, component=None):
    """ Lockup index returns a dynamic iterable which 
        actor_id is the actor that this is requested for
        component contains a list of all actor_ids of the component if the actor belongs to a component else None
    """
    index_str = format_index_string(index)
    it = node.storage.get_index_iter(index_str)
    it.set_name("attr_match")
    return it
