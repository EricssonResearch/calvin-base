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

from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.runtime.north.calvin_token import EOSToken


class Sequencer(Actor):
    """
    Interleave incoming tokens with end of string token (EOS) on outport.

    Inputs:
        data_in : Tokens, any kind.
    Outputs:
        data_out: Tokens seen on input, interleaved with EOS
    """

    @manage(['token', 'eos'])
    def init(self):
        self.token = None
        self.eos = False

    @condition(action_input=['data_in'])
    def incoming(self, token):
        self.token = token

    @stateguard(lambda self: self.token is not None)
    @condition(action_output=['data_out'])
    def send_token(self):
        token = self.token
        self.token = None
        self.eos = True
        return (token,)

    @stateguard(lambda self: self.eos)
    @condition(action_output=['data_out'])
    def send_eos(self):
        self.eos = False
        return (EOSToken(),)

    action_priority = (send_eos, send_token, incoming)


    test_set = [
        {
            'inports': {'data_in': ["A", "B", "C"]},
            'outports': {'data_out': ["A", 'End of stream', "B", 'End of stream', "C", 'End of stream']}
        }
    ]
