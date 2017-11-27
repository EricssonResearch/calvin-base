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

from calvin.actor.actor import Actor, manage, condition
from calvin.runtime.north.calvin_token import EOSToken


class PostfixString(Actor):

    """
    Appends <postfix> to input tokens and passes them to ouput port as strings
    Inputs:
      in : Text token
    Outputs:
      out : Postfixed text token
    """
    @manage(['postfix'])
    def init(self, postfix='-'):
        self.postfix = str(postfix)

    def exception_handler(self, action, args):
        return (EOSToken(), )

    @condition(['in'], ['out'])
    def postfix(self, token):
        return (str(token) + self.postfix, )

    action_priority = (postfix, )

    test_kwargs = {'postfix': 'P'}

    test_set = [
        {
            'inports': {'in': ['a', 'b', 'c']},
            'outports': {'out': ['aP', 'bP', 'cP']}
        }
    ]
