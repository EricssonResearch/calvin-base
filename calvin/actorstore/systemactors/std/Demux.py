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

from calvin.actor.actor import Actor, condition, stateguard, manage

class Demux(Actor):
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

    @manage(['select', 'incoming_mapped', 'incoming_unmapped'])
    def init(self, select):
        self.select = select
        self.incoming_mapped = []
        self.incoming_unmapped = []

    def will_start(self):
        self.outports['token'].set_config({'port-mapping':self.select})

    @condition(['token', 'select'])
    def receive(self, tok, sel):
        if sel in self.select:
            self.incoming_mapped.append((sel, tok))
        else:
            self.incoming_unmapped.append(tok)
    
    @stateguard(lambda self: self.incoming_mapped)
    @condition([], ['token'])
    def dispatch(self):
        sel, tok = self.incoming_mapped.pop(0)
        return ({sel:tok}, )
        
    @stateguard(lambda self: self.incoming_unmapped and not self.incoming_mapped)
    @condition([], ['default'])
    def dispatch_default(self):
        tok = self.incoming_unmapped.pop(0)
        return (tok,)

    action_priority = (dispatch, dispatch_default, receive)


