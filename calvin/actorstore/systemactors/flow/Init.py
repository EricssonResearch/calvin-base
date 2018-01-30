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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

class Init(Actor):

    """
    Insert an initial token (data) before passing all others through

    Inputs:
      in: Any token
    Outputs:
      out: Data given as parameter followed by data from in port
    """

    @manage(['data', 'schedule'])
    def init(self, data):
        self.data = data
        self.schedule = calvinsys.open(self, "sys.schedule")

    @stateguard(lambda self: self.schedule and calvinsys.can_read(self.schedule))
    @condition([], ['out'])
    def initial_action(self):
        calvinsys.read(self.schedule) # ack
        calvinsys.close(self.schedule)
        self.schedule = None
        return (self.data,)

    @stateguard(lambda self: not self.schedule)
    @condition(['in'], ['out'])
    def passthrough(self, data):
        return (data,)

    action_priority = (passthrough, initial_action)
    requires = ['sys.schedule']

    test_kwargs = {'data': 0}
    test_calvinsys = {'sys.schedule': {'read': ["dummy_data_read"]}}
    test_set = [
       {
           'inports': {'in': [1,2,3]},
           'outports': {'out': [0,1,2,3]},
       },
    ]
