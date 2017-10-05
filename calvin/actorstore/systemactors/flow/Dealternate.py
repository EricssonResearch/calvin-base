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

from calvin.actor.actor import Actor, condition, manage

class Dealternate(Actor):
    """
    Route tokens to the ports connected to the fan-out port token in the order given by the argument 'order'
    Inputs:
      token: Any token
    Outputs:
      token(routing="dispatch-ordered") : Dispatching tokens to connected ports in order
    """

    @manage(['order'])
    def init(self, order):
        self.order = order

    def will_start(self):
        self.outports['token'].set_config({'port-order':self.order})

    @condition(['token'], ['token'])
    def dispatch(self, tok):
        return (tok,)

    action_priority = (dispatch,)

    test_args = ["tag-1:"]
    test_set = [
        {
            'inports': {'token': ['test']},
            'outports': {'token': ['test']}
        }
    ]
