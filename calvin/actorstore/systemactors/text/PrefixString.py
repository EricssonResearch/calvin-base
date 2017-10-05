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

from calvin.actor.actor import Actor, manage, condition
from calvin.runtime.north.calvin_token import EOSToken


class PrefixString(Actor):

    """
    Prepends <prefix> to input tokens and passes them to ouput port as strings
    Inputs:
      in : Text token
    Outputs:
      out : Prefixed text token
    """
    @manage(['prefix'])
    def init(self, prefix='-'):
        self.prefix = str(prefix)

    def exception_handler(self, action, args):
        return (EOSToken(), )

    @condition(['in'], ['out'])
    def prefix(self, token):
        return (self.prefix + str(token), )

    action_priority = (prefix, )

    test_kwargs = {'prefix': 'P'}

    test_set = [
        {
            'inports': {'in': ['a', 'b', 'c']},
            'outports': {'out': ['Pa', 'Pb', 'Pc']}
        }
    ]
