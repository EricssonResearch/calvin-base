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

from calvin.actor.actor import Actor, condition, ActionResult


class Tee(Actor):
    """Sends data on input port to both output ports

    Input :
      token : any token
    Output :
      token_1 : first copy of token
      token_2 : second copy of token
    """

    def init(self):
        pass

    @condition(action_input=[('token', 1)], action_output=[('token_1', 1), ('token_2', 1)])
    def tee(self, token):
        return ActionResult(production=(token, token))

    action_priority = (tee,)
