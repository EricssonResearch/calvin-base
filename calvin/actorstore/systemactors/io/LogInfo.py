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


class LogInfo(Actor):
    """
    Write data to system log at loglevel "INFO"

    Input:
      data : data to be logged
    """

    def exception_handler(self, action_function, args):
        # The action 'log' takes a single token
        exception_token = args[0]
        return action_function(self, "Exception '%s'" % (exception_token,))

    @manage(["log"])
    def init(self):
        self.log = calvinsys.open(self, "log.info")

    @stateguard(lambda self: calvinsys.can_write(self.log))
    @condition(action_input=['data'])
    def write(self, data):
        calvinsys.write(self.log, data)

    action_priority = (write, )
    requires = ["log.info"]


    test_calvinsys = {'log.info': {'write': ['a', 'b', 'c', 'd']}}
    test_set = [
        {
            'inports': {'data': ['a', 'b', 'c', 'd']},
        }
    ]
