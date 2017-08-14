# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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


class LogWarning(Actor):
    """
    Write data to system log at loglevel "warning"

    Input:
      data : data to be logged
    """

    def exception_handler(self, action_function, args):
        # The action 'log' takes a single token
        exception_token = args[0]
        return action_function(self, "Exception '%s'" % (exception_token,))

    @manage([])
    def init(self):
        self.setup()
        
    def setup(self):
        self._log = calvinsys.open(self, "log.warning")

    def will_migrate(self):
        calvinsys.close(self._log)
    
    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: calvinsys.can_write(self._log))
    @condition(action_input=['data'])
    def log(self, data):
        calvinsys.write(self._log, data)
        

    action_priority = (log, )
    
    requires = ["log.warning"]

