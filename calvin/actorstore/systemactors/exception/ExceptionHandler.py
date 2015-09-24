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


class ExceptionHandler(Actor):

    """
    Scan tokens for Exceptions.

    Any non-exception or EOS is simply passed on. Exceptions other than EOS are replaced
    with an EOS token on the ouput 'token' port unless optional 'replace' argument is true,
    in which case 'replacement' argument (defaults to null) is produced.
    Any exception (including EOS) are produces its reason on the 'status' output port.

    Inputs:
      token  : any token
    Outputs:
      token  : input token or EOS/replacement on exception
      status : reason for any exception tokens encountered (including EOS)
    """

    def exception_handler(self, action, args, context):
        try:
            e = args[context['exceptions']['token'][0]]
        except:
            e = ExceptionToken()
        self.status = e
        self.token = EOSToken()
        return ActionResult()

    @manage(['status', 'token', 'replace', 'replacement'])
    def init(self, replace=False, replacement=None):
        self.replace = replace
        self.replacement = replacement
        self.status = None
        self.token = None

    @condition([], ['token', 'status'])
    @guard(lambda self: self.token and self.status)
    def produce_with_exception(self):
        tok = self.replacement if self.replace else self.token
        status = self.status
        self.token = None
        self.status = None
        return ActionResult(production=(tok, status.value))

    @condition([], ['token'])
    @guard(lambda self: self.token and not self.status)
    def produce(self):
        tok = self.token
        self.token = None
        return ActionResult(production=(tok,))

    @condition(['token'])
    @guard(lambda self, tok: not self.status)
    def consume(self, tok):
        self.token = tok
        self.status = None
        return ActionResult()

    action_priority = (produce_with_exception, produce, consume)

    test_set = [
        {  # normal token
            'in': {'token': 42},
            'out': {'token': [42], 'status':[]}
        },
        {  # Exception
            'in': {'token': ExceptionToken()},
            'out': {'token': ['End of stream'], 'status':['Exception']}
        },
        {  # Exception
            'in': {'token': EOSToken()},
            'out': {'token': ['End of stream'], 'status':['End of stream']}
        },
        {  # Exception with replace (default)
            'setup': [lambda self: self.init(replace=True)],
            'in': {'token': EOSToken()},
            'out': {'token': [None], 'status':['End of stream']}
        },
        {  # Exception with replace
            'setup': [lambda self: self.init(replace=True, replacement={})],
            'in': {'token': EOSToken()},
            'out': {'token': [{}], 'status':['End of stream']}
        },
        {  # Exception with replace
            'setup': [lambda self: self.init(replace=True, replacement={})],
            'in': {'token': ExceptionToken()},
            'out': {'token': [{}], 'status':['Exception']}
        },
    ]
