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

    @manage(['index', 'order', 'port_order'])
    def init(self, order):
        self.index = 0
        self.order = order

    def will_start(self):
        self.port_order = self.outports['token'].get_ordering(self.order)        
        
    @condition(['token'], ['token'], metadata=True)
    def dispatch(self, tok):
        data, meta = tok
        index = self.index
        meta['port_tag'] = self.port_order[index]
        index += 1
        self.index = index % len(self.order)
        return ((data, meta),)

    action_priority = (dispatch,)


