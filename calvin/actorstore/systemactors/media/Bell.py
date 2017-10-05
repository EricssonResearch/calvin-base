# -*- coding: utf-8 -*-

# Copyright (c) 2016-17 Ericsson AB
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
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class Bell(Actor):

    """
    Triggers a audible or visible bell (runtime dependent).

    Inputs:
      trigger: any token triggers the bell.
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._bell = calvinsys.open(self, "notify.bell")

    def did_migrate(self):
        self.setup()

    def will_end(self):
        calvinsys.close(self._bell)

    @stateguard(lambda self: calvinsys.can_write(self._bell))
    @condition(action_input=['trigger'])
    def signal(self, _):
        calvinsys.write(self._bell, None)

    action_priority = (signal, )
    requires = ['notify.bell']


    test_calvinsys = {'notify.bell': {'write': [None, None, None, None]}}
    test_set = [
        {
            'inports': {'trigger': [True, 1, "a", 0]},
        }
    ]
