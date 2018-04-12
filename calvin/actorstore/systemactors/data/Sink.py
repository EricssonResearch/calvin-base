# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Sink(Actor):
    """
    Data sink - usually some form of permanent storage

    input:
        data: a list of json structures to be saved
    """

    @manage([])
    def init(self ):
        self.sink = calvinsys.open(self, "data.sink")

    @stateguard(lambda self: calvinsys.can_write(self.sink))
    @condition(["data"], [])
    def write(self, data):
        calvinsys.write(self.sink, data)

    action_priority = (write,)
    requires = ['data.sink']
