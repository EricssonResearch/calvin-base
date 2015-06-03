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


class FileNotFoundHandler(Actor):

    """
    Scan tokens for Exceptions other than EOS.

    Any non-exception or EOS is simply passed on. Exceptions are replaced with EOS token.
    The 'status' outport indicates when an exception occurs by producing 1 instead of 0.

    Inputs:
      token  : any token
    Outputs:
      token  : input token or EOS on exception
      status : for each input token, indicate exception (1) or normal (0) token
    """

    def exception_handler(self, action, args, exceptions):
        self.token = EOSToken()
        self.status = 1
        return ActionResult(tokens_consumed=1, tokens_produced=0)

    @manage([])
    def init(self):
        self.token = None

    @condition([], ['token', 'status'])
    @guard(lambda self: self.token)
    def produce(self):
        tok = self.token
        self.token = None
        return ActionResult(tokens_consumed=0, tokens_produced=2, production=(tok, self.status))

    @condition(['token'])
    def consume(self, tok):
        self.token = tok
        self.status = 0
        return ActionResult(tokens_consumed=1)

    action_priority = (produce, consume)

    test_set = [
        {  # normal token
            'in': {'token': 42},
            'out': {'token': [42], 'status':[0]}
        },
        {  # Exception
            'in': {'token': ExceptionToken()},
            'out': {'token': ['End of stream'], 'status':[1]}
        },
    ]
