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

class Constant(Actor):
   """
   Send predetermined data on output. Never ending sequence.

   Outputs:
       token : given data
   """

   @manage(['data', 'schedule'])
   def init(self, data):
       self.data = data
       self.schedule = calvinsys.open(self, "sys.schedule")


   @stateguard(lambda self: calvinsys.can_read(self.schedule))
   @condition([], ['token'])
   def timeout(self):
       calvinsys.read(self.schedule) # ack
       calvinsys.can_write(self.schedule)
       calvinsys.write(self.schedule, 0) #reset
       return (self.data, )

   action_priority = (timeout, )
   requires = ['sys.schedule']


   test_kwargs = {'data': "data_to_forward"}
   NTOKENS = 10
   test_calvinsys = {'sys.schedule': {'read': ["dummy_data_read"]*NTOKENS, 'write': [0]*NTOKENS}}
   test_set = [
       {
           'outports': {'token': ["data_to_forward"]*NTOKENS}
       }
   ]
