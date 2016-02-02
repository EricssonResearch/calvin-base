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

from calvin.actor.actor import Actor, ActionResult, condition


class Wrapper(object):
    """Wrap a token value in 'left' and 'right', i.e. 1 => ((( 1 )))"""
    def __init__(self, left, right):
        super(Wrapper, self).__init__()
        self.left = str(left)
        self.right = str(right)

    def wrap(self, x):
        return "%s %s %s" % (self.left, str(x), self.right)


class ExplicitStateExample(Actor):

    """
    Demonstrate (and test) explicit state handling in actors.
    In order to migrate this actor, potentially to non-python platforms,
    we need to explicitly handle set/get state for the custom wrap object.
    Input:
        token : any token
    Output:
        token : a string with input token wrapped in '(((' and ')))'
    """

    def init(self):
        self.wrapper = Wrapper('(((', ')))')

    #
    # Sincle we are using a custom object as part of the that we
    # are responsible for making this actor type migratable by
    # providing state() and set_state() taking care of conversion
    # of object to and from a serializable representation.
    # N.B. Mandatory use of calls to super's state and set_state
    #      to handle all other state variables.
    #
    def state(self):
        state = super(ExplicitStateExample, self).state()
        # Create a serializable representation of instance
        state['wrapper'] = [self.wrapper.left, self.wrapper.right]
        return state

    def _set_state(self, state):
        l, r = state.pop('wrapper')
        # Create an instance from a serialized representation
        self.wrapper = Wrapper(l, r)
        super(ExplicitStateExample, self)._set_state(state)

    @condition(['token'], ['token'])
    def wrap_action(self, input):
        return ActionResult(production=(self.wrapper.wrap(input), ))

    action_priority = (wrap_action,)

    def verify(self, helper):
        helper.write('token', 1)
        helper.loop_once()
        assert helper.read('token') == '((( 1 )))'
