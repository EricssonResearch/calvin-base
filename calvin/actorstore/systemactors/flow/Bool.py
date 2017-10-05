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
from calvin.utilities.calvinlogger import get_actor_logger


_log = get_actor_logger(__name__)


class Bool(Actor):
    """
    Any token on the inport will be tested for truth value.
    The following values are considered false:

    null
    false
    zero of any numeric type, for example, 0, 0L, 0.0, 0j
    any empty sequence, for example, "", (), []
    any empty mapping, for example, {}

    All other values are considered true

    Inputs:
      token : a token to evaluate to either true or false
    Outputs:
      bool : true or false
    """
    @manage()
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        pass

    @condition(['token'], ['bool'])
    def test(self, token):
        return (bool(token), )

    action_priority = (test, )

    test_set = [
        {
            'inports': {'token': [None, 0, 0.0, 0L, 0j, "", [], {}, False]},
            'outports': {'bool': [False]*9},
        },
        {
            'inports': {'token': [1, 2, 3.0, 1L, 2j, "Some string", [1, 2], {"a": 2}, True]},
            'outports': {'bool': [True]*9},
        },
    ]
