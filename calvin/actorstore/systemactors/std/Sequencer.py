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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.runtime.north.calvin_token import EOSToken


class Sequencer(Actor):
    """
    Interleave incoming tokens with EOS on outport.

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
        return ActionResult()

    @condition(action_output=['data_out'])
    @guard(lambda self: self.token is not None)
    def send_token(self):
        token = self.token
        self.token = None
        self.eos = True
        return ActionResult(production=(token,))

    @condition(action_output=['data_out'])
    @guard(lambda self: self.eos)
    def send_eos(self):
        self.eos = False
        return ActionResult(production=(EOSToken(),))

    action_priority = (incoming, send_token, send_eos)
