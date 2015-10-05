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

# encoding: utf-8

from calvin.actor.actor import Actor, ActionResult, manage, condition
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken


class FromString(Actor):
    """
    Transform JSON-formatted string to value

    Invalid input will produce an Exception token as output unless another value is supplied
    through the optional 'exception_output' argument.
    N.B. Using 'null' for 'exception_output' will produce an ExceptionToken rather than 'null'.

    Inputs:
      string : JSON-formatted string
    Outputs:
      data   : data read from input string
    """

    def exception_handler(self, action, args, context):
        return ActionResult(production=(self.default,))

    @manage(['default'])
    def init(self, exception_output=None):
        self.default = ExceptionToken() if exception_output is None else exception_output
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.use('calvinsys.native.python-json', shorthand='json')

    @condition(['string'], ['data'])
    def load(self, string):
        try:
            res = self['json'].loads(string)
        except:
            res = self.default
        return ActionResult(production=(res,))

    action_priority = (load,)
    require = ['calvinsys.native.python-json']

    test_set = [
        {
            'in': {'string': ['1']},
            'out': {'data': [1]},
        },
        {
            'in': {'string': ['{"a": 1}']},
            'out': {'data': [{"a": 1}]},
        },
        {
            'in': {'string': [EOSToken()]},
            'out': {'data': ['Exception']},
        },
        {
            'in': {'string': [None]},
            'out': {'data': ['Exception']},
        },
        {
            'setup': [lambda self: self.init(exception_output={})],
            'in': {'string': [None]},
            'out': {'data': [{}]},
        },
    ]
