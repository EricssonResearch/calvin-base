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

    @manage(['mapping'])
    def init(self, mapping):
        self.mapping = mapping

    def will_start(self):
        self.inports['token'].set_config({'port-mapping':self.mapping})

    @condition(['token'], ['dict'])
    def collect_tokens(self, token):
        return (token,)

    action_priority = (collect_tokens, )


    test_kwargs = {'mapping': 'dummy'}
    test_set = [
        {
            'inports': {'token': ["a", "b", 1]},
            'outports': {'dict': ["a", "b", 1]}
        }
    ]
