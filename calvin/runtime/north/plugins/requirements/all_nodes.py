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

def _req_op_cb(key, value, cb):
    cb(value if value else None)

def req_op(node, cb, actor_id=None, component=None):
    """ Lockup all nodes that have registered a node_name """
    node.storage.get_index(format_index_string(("node_name", {})), CalvinCB(_req_op_cb, cb=cb))
