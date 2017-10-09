# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

from calvin.actor.actor import Actor, condition, manage

from calvin.utilities.calvinlogger import get_actor_logger
_log = get_actor_logger(__name__)

class CollectDict(Actor):
    """
    Collect tokens from token port, forming a dict according to mapping. May produce
    a partial dictionary.

    Inputs:
      token(routing="collect-any-tagged"): token
    Outputs:
      dict : Collected dictionary according to 'mapping'
    """

    # Using collect_any queue

    @manage(['mapping'])
    def init(self, mapping):
        self.mapping = mapping

    def will_start(self):
        # At this time, ports are connected and have a port_id,
        # change mapping from {<key>:&actor.port, ...} -> {<port_id>:<key>, ..}
        # using identity &actor.port === <port_id>
        self.mapping = self.inports['token'].get_reverse_mapping(self.mapping)

    # FIXME: Build dict until same port tag appears again => produce
    #        If dict not empty when inport is => produce
    @condition(['token'], ['dict'], metadata=True)
    def collect_tokens(self, inval):
        data, meta = inval
        port_id = meta.pop('port_tag', 'MISSING PORT TAG')
        key = self.mapping.get(port_id, port_id)
        retval = {key:data}
        return ((retval, meta),)

    action_priority = (collect_tokens, )
