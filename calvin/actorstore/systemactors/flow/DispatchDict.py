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

from calvin.actor.actor import Actor, condition, stateguard, manage

class DispatchDict(Actor):
    """
    Route tokens to the ports connected to the fan-out port token according to 'mapping'

    For unrecognized mappings tokens are routed to 'default' port.

    Inputs:
      dict: dictionary
    Outputs:
      token(routing="dispatch-mapped") : Dispatching tokens to connected ports according to 'mapping' 
      default: Default route for unknown token values
    """

    @manage(['mapping', 'mapped_out', "unmapped_out"]) 
    def init(self, mapping):
        self.mapped_out = {}
        self.unmapped_out = {}
        self.mapping = mapping

    def will_start(self):
        # At this time, ports are connected and all destinations have a port_id,
        # change mapping from {<key>:&actor.port, ...} -> {<key>:<port_id>, ..}
        # using identity &actor.port === <port_id>
        self.mapping = self.outports['token'].get_mapping(self.mapping)
        print "mapping:", self.mapping


    # FIXME: Propagate metadata
    @stateguard(lambda self: not self.mapped_out and not self.unmapped_out)
    @condition(['dict'], [],  metadata=True)
    def get_dict(self, data):
        dictionary, meta = data
        for key, value in dictionary.iteritems():
            if key in self.mapping :
                self.mapped_out[key] = (value, meta)
            else :
                self.unmapped_out[key] = (value, meta)

    @stateguard(lambda self: self.mapped_out)
    @condition([], ['token'], metadata=True)
    def dispatch_token(self):
        key = self.mapped_out.keys()[0]
        val, meta = self.mapped_out.pop(key)
        meta['port_tag'] = self.mapping[key]
        return ((val, meta),)

    @stateguard(lambda self: self.unmapped_out)
    @condition([], ['default'], metadata=True)
    def dispatch_default(self):
        key = self.unmapped_out.keys()[0]
        val, meta = self.unmapped_out.pop(key)
        return ((val, meta),)


    action_priority = (dispatch_token, dispatch_default, get_dict)

