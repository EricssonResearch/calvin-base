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
from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)


def req_op(node, requires, actor_id=None, component=None):
    """ Based on requires find any nodes with all those capabilities
    """
    if not requires:
        _log.analyze(node.id, "+ NO REQUIRES", {'actor_id': actor_id})
        return dynops.Infinite(cb)

    iters = []
    for r in requires:
        _log.analyze(node.id, "+", {'req_cap': r})
        iters.append(node.storage.get_index_iter(['node', 'capabilities', r]))

    it = dynops.Intersection(*iters)
    it.set_name("actor_reqs_match")
    return it