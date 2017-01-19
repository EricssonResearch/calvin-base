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
        self.use("calvinsys.io.stdout", shorthand="stdout")
        self.stdout = self["stdout"]
        self.stdout.enable()
                
    def will_migrate(self):
        self.stdout.disable()
        
    def did_migrate(self):
        self.setup()

    @condition(action_input=['token'])
    def write(self, data):
        self.stdout.writeln(str(data))
        

    action_priority = (write, )
    
    requires = ['calvinsys.io.stdout']
    
