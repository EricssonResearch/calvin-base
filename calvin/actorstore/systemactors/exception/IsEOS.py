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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken


class IsEOS(Actor):

    """
    Return 'true' if token is EOS-token


    Inputs:
      token  : any token
    Outputs:
      status : 'true' if input token is EOS-token, false otherwise
    """

    def exception_handler(self, action, args, context):
        self.token = type(args[0]) is EOSToken
        return ActionResult()

    @manage([])
    def init(self):
        self.token = None

    @condition([], ['status'])
    @guard(lambda self: self.token is not None)
    def produce(self):
        tok = self.token
        self.token = None
        return ActionResult(production=(tok,))

    @condition(['token'])
    @guard(lambda self, tok: self.token is None)
    def consume(self, tok):
        self.token = False
        return ActionResult()

    action_priority = (produce, consume)

    test_set = [
        {  # normal token
            'in': {'token': 42},
            'out': {'status':[False]}
        },
        {  # Exception
            'in': {'token': ExceptionToken()},
            'out': {'status':[False]}
        },
        {  # Exception
            'in': {'token': EOSToken()},
            'out': {'status':[True]}
        },

    ]
