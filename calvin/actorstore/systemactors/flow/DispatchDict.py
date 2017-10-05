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
        self.outports['token'].set_config({'port-mapping':self.mapping})

    @stateguard(lambda self: not self.mapped_out and not self.unmapped_out)
    @condition(['dict'], [])
    def get_dict(self, dictionary):
        for key, value in dictionary.iteritems():
            if key in self.mapping :
                self.mapped_out[key] = value
            else :
                self.unmapped_out[key] = value
        return ()

    @stateguard(lambda self: self.mapped_out)
    @condition([], ['token'])
    def dispatch_token(self):
        key = self.mapped_out.keys()[0]
        val = self.mapped_out.pop(key)
        return ({key:val},)

    @stateguard(lambda self: self.unmapped_out)
    @condition([], ['default'])
    def dispatch_default(self):
        key = self.unmapped_out.keys()[0]
        val = self.unmapped_out.pop(key)
        return (val,)

    action_priority = (dispatch_token, dispatch_default, get_dict)

    test_kwargs = {'mapping': 'dummy'}
    test_set = [
        {
            'inports': {'dict': [{"a": 1}, {"b": 2}, {"c": 3}]},
            'outports': {'token': [],
                         'default': [1, 2, 3]}
        }
    ]
