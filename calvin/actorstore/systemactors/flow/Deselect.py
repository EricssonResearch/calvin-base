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


class Deselect(Actor):
    """
    Route token from 'case_true' or 'case_false' to 'data' port depending on 'select'

    Deselect assumes 'false' or 'true' as input, values outside that
    range will default to 'case_false'.

    Inputs:
      case_false  : Token to output 'data' if select token is 'false'
      case_true   : Token to output 'data' if select token is 'true'
      select : Select which inport will propagate to 'data' port
    Outputs:
      data  : Token from 'case_true' or 'case_false' port
    """
    @manage(['select'])
    def init(self):
        self.select = None


    @stateguard(lambda self: self.select is None)
    @condition(['select'], [])
    def select_action(self, select):
        self.select = select is True
        # Default to false if select value is not true or false
        


    @stateguard(lambda self: self.select is False)
    @condition(['case_false'], ['data'])
    def false_action(self, data):
        self.select = None
        return (data, )

    @stateguard(lambda self : self.select is True)
    @condition(['case_true'], ['data'])
    def true_action(self, data):
        self.select = None
        return (data, )


    action_priority = (false_action, true_action, select_action)

    test_set = [
        {
            'inports': {
                'case_false': ['a', 'b', 'c'],
                'case_true':['A', 'B', 'C'],
                'select': [True, False]*3
            },
            'data': {'port': ['A', 'a', 'B', 'b', 'C', 'c']},
        },
    ]
