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


class IsEOS(Actor):

    """
    Return 'true' if token is EOS-token


    Inputs:
      token  : any token
    Outputs:
      status : 'true' if input token is EOS-token, false otherwise
    """

    def exception_handler(self, action, args):
        self.token = type(args[0]) is EOSToken


    @manage([])
    def init(self):
        self.token = None

    @stateguard(lambda self: self.token is not None)
    @condition([], ['status'])
    def produce(self):
        tok = self.token
        self.token = None
        return (tok,)

    @stateguard(lambda self: self.token is None)
    @condition(['token'])
    def consume(self, tok):
        self.token = False


    action_priority = (produce, consume)

    test_set = [
        {  # normal token
            'inports': {'token': 42},
            'outports': {'status':[False]}
        },
        {  # Exception
            'inports': {'token': ExceptionToken()},
            'outports': {'status':[False]}
        },
        {  # Exception
            'inports': {'token': EOSToken()},
            'outports': {'status':[True]}
        },

    ]
