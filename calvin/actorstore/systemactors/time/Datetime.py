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

from calvin.actor.actor import Actor, manage, condition, calvinlib

class Datetime(Actor):
    """
    Return a dictionary with current date and time.

    The dictionary contains entries for:
    century, year, month, day, hour, minute, second, timezone

    Input:
      trigger : any token

    Output:
      datetime : dictionary
    """

    @manage([])
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.time = calvinlib.use('time')

    @condition(['trigger'], ['datetime'])
    def action(self, consume_trigger):
        return (self.time.datetime(),)

    action_priority = (action,)
    requires = ['time']


    test_set = [
        {
            'inports': {'trigger': [True]}
        }
    ]
