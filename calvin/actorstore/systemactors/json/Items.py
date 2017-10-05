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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib
from calvin.runtime.north.calvin_token import  ExceptionToken
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)

class Items(Actor):

    """
    Produce all items from a list as a sequence of tokens.

    Produce an exception token if data is not a list.

    Inputs:
      list:  a list
    Outputs:
      item: items of list in order
    """


    @manage(['data', 'has_data'])
    def init(self):
        self.data = []
        self.has_data = False
        self.setup()

    def setup(self):
        self.copy = calvinlib.use("copy")

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: not self.has_data)
    @condition(['list'], [])
    def consume_list(self, data):
        if type(data) is not list:
            self.data = [ExceptionToken()]
            self.has_data = True
            return
        if not data:
            # Empty list => no output
            return
        try:
            self.data = self.copy.copy(data)
            self.has_data = True
        except Exception as e:
            _log.info("An error occurred: {}".format(e))

    @stateguard(lambda self: self.has_data)
    @condition([], ['item'])
    def produce_item(self):
        res = self.data.pop(0)
        if not self.data:
            self.data = []
            self.has_data = False
        return (res, )

    action_priority = (produce_item, consume_list)
    requires = ['copy']


    test_args = []
    test_kwargs = {}
    test_set = [
        {
            'inports': {'list': [[1,2,3]]},
            'outports': {'item': [1,2,3]},
        },
        {
            'inports': {'list': [[], [], [1,2,3]]},
            'outports': {'item': [1,2,3]},
        },

        # Error conditions
        {
            'inports': {'list': [1]},
            'outports': {'item': ['Exception']},
        },

    ]
