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

from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.runtime.north.calvin_token import EOSToken
import sys
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)

class FiniteCounter(Actor):
    """
    Produce next token in a sequence start, start+1, ..., start+steps-1, EOSToken
    If repeat is True will repeat sequence
    Outputs:
      integer : Integer
    """

    @manage(['count', 'ends', 'restart', 'start', 'replicate_mult', 'stopped'])
    def init(self, start=0, steps=sys.maxint, repeat=False, replicate_mult=False, stopped=False):
        self.count = start
        self.ends = start + steps
        self.restart = start if repeat else self.ends + 1
        self.start = start
        self.replicate_mult = replicate_mult
        self.stopped = stopped

    def did_replicate(self, index):
        diff = self.start * index if self.replicate_mult else 0
        # Offset by diff for each new replica
        self.count += diff
        self.ends += diff
        self.restart += diff

    @stateguard(lambda self: not self.stopped and self.count < self.ends)
    @condition(action_output=['integer'])
    def cnt(self):
        #_log.info("FinitCounter (%s, %s, %s) count:%s" % (self._name, self._id, self.outports['integer'].id, self.count))
        self.count += 1
        return (self.count - 1, )

    @stateguard(lambda self: not self.stopped and self.count == self.ends)
    @condition(action_output=['integer'])
    def the_end(self):
        self.count = self.restart
        return (EOSToken(), )

    action_priority = (cnt, the_end)

    def report(self, **kwargs):
        self.stopped = kwargs.get("stopped", self.stopped)
        return self.count

    test_args = []
    test_set = [
            {
            'setup': [lambda self: self.init(steps=3)],
            'inports': {},
            'outports': {'integer': [0, 1, 2, EOSToken().value]}
            },
    ]
