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

from calvin.actor.actor import Actor, manage, condition, calvinlib
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken


class ToString(Actor):
    """
    documentation:
    - Transform data to JSON-string
    - Exception tokens will value is supplied
      through the 'exception_output' argument.
    ports:
    - direction: in
      help: any kind of token
      name: data
    - direction: out
      help: JSON-formatted string
      name: string
    """

    def exception_handler(self, action, args):
        return (self.json.tostring(self.default),)

    @manage(['default'])
    def init(self, exception_output):
        self.default = exception_output
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.json = calvinlib.use("json")


    @condition(['data'], ['string'])
    def dump(self, value):
        return (self.json.tostring(value),)

    action_priority = (dump,)
    requires = ['json']


    test_set = [
        {
            'inports': {'data': [1]},
            'outports': {'string': ['1']},
        },
        {
            'inports': {'data': [{"a": 1}]},
            'outports': {'string': ['{"a": 1}']},
        },
        {
            'inports': {'data': [EOSToken()]},
            'outports': {'string': ['null']},
        },
        {
            'inports': {'data': [ExceptionToken()]},
            'outports': {'string': ['null']},
        },
        {
            'setup': [lambda self: self.init(exception_output={})],
            'inports': {'data': [ExceptionToken()]},
            'outports': {'string': ['{}']},
        },
    ]
