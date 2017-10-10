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

class CollectCompleteDict(Actor):
    """
    Collect tokens from token port, forming a dict according to mapping. Will only produce
    a complete dictionary.

    Inputs:
      token(routing="collect-all-tagged"): token
    Outputs:
      dict : Collected dictionary according to 'mapping' 
    """

    @manage(['mapping'])
    def init(self, mapping):
        self.mapping = mapping

    def will_start(self):
        self.mapping = self.inports['token'].get_reverse_mapping(self.mapping)
        

    @condition(['token'], ['dict'], metadata=True)
    def collect_tokens(self, token):
        data, meta = token
        keys = [self.mapping.get(x, x) for x in meta['port_tag']]
        retval = dict(zip(keys, data))
        return ((retval, {}),)

    action_priority = (collect_tokens, )

    test_args = []
    test_kwargs = {'select':{}}
