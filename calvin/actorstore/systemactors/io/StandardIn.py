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


class StandardIn(Actor):
    """
    Reads from Standard IN, and send each read line as a token on output port

    Outputs:
      out : Each token is a line of text, or EOSToken.
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self.file = calvinsys.open(self, "io.stdin")

    def did_migrate(self):
        self.setup()

    def will_end(self):
        if self.file is not None:
            calvinsys.close(self.file)
            self.file = None

    @stateguard(lambda self: self.file and calvinsys.can_read(self.file))
    @condition([], ['out'])
    def read(self):
        line = calvinsys.read(self.file)
        return (line, )

    action_priority = (read, )
    requires = ['io.stdin']
    
    test_calvinsys = {'io.stdin': {'read': ['the', 'quick', 'brown', 'fox', 'jumped', 'over', 'the', 'lazy', 'dog']}}
    test_set = [
        {
            'outports': {'out': ['the', 'quick', 'brown', 'fox', 'jumped', 'over', 'the', 'lazy', 'dog']},
        }
    ]
