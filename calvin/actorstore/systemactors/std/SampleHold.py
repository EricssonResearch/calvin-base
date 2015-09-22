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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from copy import copy

class SampleHold(Actor):
    """
    Sample 'in' and hold it internally if 'sample' input is true, replacing any previous value.

    Produce the held token on the 'out' port regardless of wether 'sample' is true or false.
    Assumes 'false' or 'true' as input to 'sample', other values are considered 'false'.

    Inputs:
      sample : Sample 'in' if true.
      in     : A token
    Outputs:
      out    : The currently held token, or the 'default' argument if not sampled yet.
    """

    @manage(['held'])
    def init(self, default=None):
        self.held = default

    @condition(['sample', 'in'], ['out'])
    def action(self, sample, tok):
        if sample is True:
            self.held = copy(tok)
        return ActionResult(production=(self.held, ))

    action_priority = (action,)

    test_args = [-1]

    test_set = [
        {
            'in': {'in': [0, 1, 2, 3], 'sample': [False, True, 1, True]},
            'out': {'out': [-1, 1, 1, 3]},
        },
    ]
