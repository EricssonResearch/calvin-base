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

from calvin.actor.actor import Actor, ActionResult, condition, guard, manage

class DemuxN(Actor):
    """
    Route tokens to the ports connected to the fan-out port token given by the argument 'select' mapping

    For values of the 'select' token not present in select mapping tokens are routed to 'default' port.

    Inputs:
      token: Any token
      select: Route 'token' accordingly
    Outputs:
      token(routing="dispatch-mapped") : Dispatching tokens to connected ports according to 'select' token value
      default: Default route for unknown 'select' token values
    """

    @manage(['select'])
    def init(self, select):
        self.select = select

    def will_start(self):
        self.outports['token'].set_config({'port-mapping':self.select})

    @condition(['token', 'select'], ['token'])
    @guard(lambda self, tok, sel: sel in self.select)
    def dispatch(self, tok, sel):
        # The use of {sel:tok} dict is in analogy with how the collect inports work
        return ActionResult(production=({sel:tok}, ))

    @condition(['token', 'select'], ['default'])
    @guard(lambda self, tok, sel: sel not in self.select)
    def dispatch_default(self, tok, sel):
        return ActionResult(production=(tok, ))

    action_priority = (dispatch, dispatch_default)

    test_args = []
    test_kwargs = {'select':{}}

    test_set = [
        {
            'in': {'token': [1, 2], 'select': ["foo", "bar"]},
            'out': {'token': [], 'default': [1, 2]},
        },
    ]

