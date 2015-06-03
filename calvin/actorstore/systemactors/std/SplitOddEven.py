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


class SplitOddEven(Actor):
    """
    Split a stream of numbers into even/odd
    Inputs:
      integer : Number
    Outputs:
      odd : odd numbers
      even : even numbers
    """
    @manage(['dump'])
    def init(self, dump=False):
        self.dump = dump

    def is_even(self, input):
        val = input if isinstance(input, (int, long)) else 0
        return (val % 2) == 0

    def is_odd(self, input):
        return not self.is_even(input)

    def log(self, data):
        print "%s<%s>: %s" % (self.__class__.__name__, self.id, data)

    @condition(['integer'], ['even'])
    @guard(is_even)
    def even(self, input):
        if self.dump:
            self.log(input)
        return ActionResult(tokens_consumed=1, tokens_produced=1, production=(input, ))

    @condition(['integer'], ['odd'])
    @guard(is_odd)
    def odd(self, input):
        if self.dump:
            print "SplitOddEven<%s> : " % (self.id, ), input
        return ActionResult(tokens_consumed=1, tokens_produced=1, production=(input, ))

    action_priority = (even, odd)

    test_set = [
        {
            'in': {'integer': [1, 2, 3, 4]},
            'out': {'odd': [1, 3], 'even': [2, 4]}
        }
    ]
