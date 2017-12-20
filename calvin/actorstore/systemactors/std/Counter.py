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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

class Counter(Actor):
    """
    Produce next integer in a sequence 1,2,3,...
    Outputs:
      integer : Integer
    """

    @manage(['count', 'stopped', 'schedule'])
    def init(self):
        self.count = 0
        self.stopped = False
        self.schedule = calvinsys.open(self, "sys.schedule")

    @stateguard(lambda self: not self.stopped and calvinsys.can_read(self.schedule))
    @condition(action_output=['integer'])
    def cnt(self):
        calvinsys.read(self.schedule) # ack
        calvinsys.can_write(self.schedule)
        calvinsys.write(self.schedule, 0) #reset
        self.count += 1
        return (self.count, )

    action_priority = (cnt,)
    requires = ['sys.schedule']


    def report(self, **kwargs):
        self.stopped = kwargs.get("stopped", self.stopped)
        return self.count

    NTOKENS = 10
    test_calvinsys = {'sys.schedule': {'read': ["dummy_data_read"]*NTOKENS, 'write': [0]*NTOKENS}}
    test_set = [
        {'outports': {'integer': list(range(1, NTOKENS+1))}}
    ]

