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

from calvin.actor.actor import Actor, ActionResult, manage, condition, stateguard
from calvin.runtime.north.calvin_token import EOSToken
import sys

class FiniteCounter(Actor):
    """
    Produce next token in a sequence start, start+1, ..., start+steps-1, EOSToken
    If repeat is True will repeat sequence
    Outputs:
      integer : Integer
    """

    @manage(['count', 'ends', 'restart', 'start', 'replicate_mult'])
    def init(self, start=0, steps=sys.maxint, repeat=False, replicate_mult=False):
        self.count = start
        self.ends = start + steps
        self.restart = start if repeat else self.ends + 1
        self.start = start
        self.replicate_mult = replicate_mult

    def will_replicate(self, state):
        if state.replication_count > 0 and self.replicate_mult:
            m = state.replication_count + 1
        else:
            m = 1
        state.count = self.start * m

    @stateguard(lambda self: self.count < self.ends)
    @condition(action_output=['integer'])
    def cnt(self):
        self.count += 1
        return ActionResult(production=(self.count - 1, ))

    @stateguard(lambda self: self.count == self.ends)
    @condition(action_output=['integer'])
    def the_end(self):
        self.count = self.restart
        return ActionResult(production=(EOSToken(), ))

    action_priority = (cnt, the_end)

    def report(self):
        return self.count

    test_args = []
    test_set = [
            {
            'setup': [lambda self: self.init(steps=3)],
            'in': {},
            'out': {'integer': [0, 1, 2, EOSToken().value]}
            },
    ]
