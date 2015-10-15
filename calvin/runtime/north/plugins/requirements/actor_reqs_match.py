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
from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)

def _requires_cb(key, value, counter, capabilities, cb, actor_id, component):
    counter[0] -= 1
    _log.debug("actor_match_cb counter=%d, value=%s" % (counter[0], value))
    if value is not None:
        capabilities[key] = value
    if counter[0] > 0:
        # Waiting for more responses
        return
    # We got all responses, do intersection to get the possible nodes
    node_ids = set.intersection(*[set(c) for c in capabilities.values()])
    _log.debug("actor_match_cb DONE node_ids=%s" % node_ids)
    cb(node_ids)

def req_op(node, cb, requires, actor_id=None, component=None):
    """ Based on signature find actors' requires in global storage,
        filter actors based on params that are supplied
        and find any nodes with those capabilities
    """
    if not requires:
        cb(None)
        return
    l = [len(requires)]
    capabilities = {}
    for r in requires:
        _log.analyze(node.id, "+", {'req_cap': r})
        node.storage.get_index(['node', 'capabilities', r], cb=CalvinCB(_requires_cb,
                                                                            counter=l,
                                                                            capabilities=capabilities,
                                                                            actor_id=actor_id, 
                                                                            component=component,
                                                                            cb=cb))
