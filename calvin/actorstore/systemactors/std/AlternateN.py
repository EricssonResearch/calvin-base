# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

from calvin.actor.actor import Actor, ActionResult, condition, manage

class AlternateN(Actor):
    """
    Fetch tokens from the fan-in port in the order given by the argument 'order'
    Inputs:
      token(routing="collect-ordered"): incoming tokens from connected ports in order
    Outputs:
      token : tokens collected from ports as given by order
    """

    @manage(['order'])
    def init(self, order):
        self.order = order

    def will_start(self):
        self.inports['token'].set_config({'port-order':self.order})

    @condition(['token'], ['token'])
    def dispatch(self, tok):
        return ActionResult(production=(tok, ))

    action_priority = (dispatch,)

    test_args = []
    test_kwargs = {'order':[]}

    test_set = [
        {
            'in': {'token': [1]},
            'out': {'token': [1]},
        },
    ]

