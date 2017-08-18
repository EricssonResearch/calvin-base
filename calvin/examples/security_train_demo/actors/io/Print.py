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

from calvin.actor.actor import Actor, manage, condition, calvinsys, stateguard

class Print(Actor):
    """
    Print data to standard out of runtime. Note that what constitutes standard out varies.

    Input:
      token : data to write
    """

    def exception_handler(self, action, args):
        # Check args to verify that it is EOSToken
        return action(self, *args)

    @manage(exclude=['stdout'])
    def init(self):
        self.setup()

    def setup(self):
        self.stdout = calvinsys.open(self, "io.stdout")

    def will_migrate(self):
        calvinsys.close(self.stdout)
        
    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: calvinsys.can_write(self.stdout))
    @condition(action_input=['token'])
    def write(self, data):
        calvinsys.write(self.stdout, data)

    action_priority = (write, )
    
    requires = ['io.stdout']
    
