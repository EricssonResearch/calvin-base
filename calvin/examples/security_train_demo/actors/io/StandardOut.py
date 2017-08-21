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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class StandardOut(Actor):
    """
    Write tokens to standard output
    Input:
      token : Any token
    """

    def exception_handler(self, action, args, context):
        # Check args to verify that it is EOSToken
        return action(self, *args)

    @manage(['tokens', 'store_tokens', 'quiet'])
    def init(self, store_tokens=False, quiet=False):
        self.store_tokens = store_tokens
        self.tokens = []
        self.quiet = quiet
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        if self.quiet:
            self.logger = _log.debug
        else:
            self.logger = _log.info

    @condition(action_input=['token'])
    def log(self, token):
        if self.store_tokens:
            self.tokens.append(token)
        self.logger("%s<%s>: %s" % (self.__class__.__name__, self.id, str(token).strip()))

    action_priority = (log, )

    def report(self):
        return self.tokens

    test_kwargs = {'store_tokens': True}

    test_set = [
        {
            'in': {'token': ['aa', 'ba', 'ca', 'da']},
            'out': {},
            'postcond': [lambda self: self.tokens == ['aa', 'ba', 'ca', 'da']]
        }
    ]
