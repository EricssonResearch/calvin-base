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

class DealternateN(Actor):
    """
    Route tokens to the ports connected to the fan-out port token in the order given by the argument 'order'
    Inputs:
      token: Any token
    Outputs:
      token(routing="dispatch-tagged") : Dispatching tokens to connected ports in order
    """

    @manage(['order', 'order_id', 'next'])
    def init(self, order):
        self.order = order

    def will_start(self):
        self.outports['token'].set_config({'port-order':self.order})
        # port_to_id = {}
        # endpoints = self.outports['token'].endpoints
        # print "ZZZZZZZZ {}".format(self.outports['token'].queue)
        # for ep in endpoints:
        #     _, actor = ep.peer_port.owner._name.rsplit(':', 1)
        #     print "XXXXXXXX {} {} {}".format(actor, ep.peer_port.name, ep.peer_port.id)
        # #     port_to_id["{}.{}".format(actor, ep.peer_port.name)] = ep.peer_port.id
        # # self.order_id = [port_to_id[p] for p in self.order]
        # # self.order = None

    @condition(['token'], ['token'])
    def dispatch(self, tok):
        # retval = collected[self.order_id[self.next]]
        # self.next = (self.next + 1) % len(self.order_id)
        # retval = tok
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

