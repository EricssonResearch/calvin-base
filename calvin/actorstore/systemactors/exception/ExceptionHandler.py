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

from calvin.actor.actor import Actor, manage, condition, stateguard
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

    def exception_handler(self, action, args):
        try:
            e = args[0]
        except:
            e = ExceptionToken()
        self.status = e
        self.token = EOSToken()

    @manage(['status', 'token', 'replace', 'replacement'])
    def init(self, replace=False, replacement=None):
        self.replace = replace
        self.replacement = replacement
        self.status = None
        self.token = None

    @stateguard(lambda self: self.token is not None and self.status)
    @condition([], ['token', 'status'])
    def produce_with_exception(self):
        tok = self.replacement if self.replace else self.token
        status = self.status
        self.token = None
        self.status = None
        return (tok, status.value)

    @stateguard(lambda self: self.token is not None and not self.status)
    @condition([], ['token'])
    def produce(self):
        tok = self.token
        self.token = None
        return (tok,)

    @stateguard(lambda self: not self.status and self.token is None)
    @condition(['token'])
    def consume(self, tok):
        self.token = tok
        self.status = None


    action_priority = (produce_with_exception, produce, consume)

    test_set = [
        {  # normal token
            'inports': {'token': 42},
            'outports': {'token': [42], 'status':[]}
        },
        {  # Exception
            'inports': {'token': ExceptionToken()},
            'outports': {'token': ['End of stream'], 'status':['Exception']}
        },
        {  # Exception
            'inports': {'token': EOSToken()},
            'outports': {'token': ['End of stream'], 'status':['End of stream']}
        },
        {  # Long list with Exceptions in middle
            'setup': [lambda self: self.init(replace=True, replacement="EOS")],
            'inports': {'token': [0, 1, 2, EOSToken(), 0, 1, 2, EOSToken(), 0, 1, 2]},
            'outports': {'token': [0, 1, 2, 'EOS', 0, 1, 2, 'EOS', 0, 1, 2], 'status':['End of stream', 'End of stream']}
        },
        {  # Exception with replace (default)
            'setup': [lambda self: self.init(replace=True)],
            'inports': {'token': EOSToken()},
            'outports': {'token': [None], 'status':['End of stream']}
        },
        {  # Exception with replace
            'setup': [lambda self: self.init(replace=True, replacement={})],
            'inports': {'token': EOSToken()},
            'outports': {'token': [{}], 'status':['End of stream']}
        },
        {  # Exception with replace
            'setup': [lambda self: self.init(replace=True, replacement={})],
            'inports': {'token': ExceptionToken()},
            'outports': {'token': [{}], 'status':['Exception']}
        },
    ]
