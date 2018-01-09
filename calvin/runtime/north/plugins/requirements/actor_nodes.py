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
import calvin.requests.calvinresponse as response

req_type = "placement"

def req_op(node, actor_id=None, component=None):
    """ Returns any node that have the actor """
    if not actor_id:
        #empty
        it = dynops.List()
        it.set_name("actor_nodes_empty")
        it.final()
        return it
    it = dynops.List()
    it.set_name("actor_nodes")
    def _got_actor(key, value):
        try:
            it.append(value['node_id'])
        except:
            pass
        it.final()
    node.storage.get_actor(actor_id=actor_id, cb=_got_actor)
    return it
