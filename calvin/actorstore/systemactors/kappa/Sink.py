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
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class Sink(Actor):
    """
    Sink for kappa results. Parameter buffer_size determines maximum number of items to hold
    Input:
      in : Any token
    """

    def exception_handler(self, action, args):
        # Check args to verify that it is EOSToken
        return action(self, *args)

    @manage(['tokens', 'buffer_size'])
    def init(self, buffer_size=5):
        self.tokens = []
        self.buffer_size = buffer_size if buffer_size < 10 else 10

    @stateguard(lambda actor: len(actor.tokens) < actor.buffer_size)
    @condition(action_input=['in'])
    def store(self, token):
        self.tokens.append(token)

    action_priority = (store, )

    def report(self, **kwargs):
        if len(self.tokens) > 0:
            return self.tokens.pop(0)
        else :
            return None

    test_set = [
        {
            'inports': {'in': ['aa', 'ba', 'ca', 'da']},
            'outports': {},
            'postcond': [lambda self: self.tokens == ['aa', 'ba', 'ca', 'da']]
        }
    ]

    requires = ['kappa']
