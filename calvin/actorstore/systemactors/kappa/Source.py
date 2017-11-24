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

from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class Source(Actor):
    """
    Load up tokens for a kappa
    Output:
      out : Any token
    """

    def exception_handler(self, action, args):
        # Check args to verify that it is EOSToken
        return action(self, *args)

    @manage(['tokens'])
    def init(self):
        self.tokens = []

    @stateguard(lambda actor: len(actor.tokens) > 0)
    @condition(action_output=['out'])
    def send(self):
        return (self.tokens.pop(0),)
        
    def report(self, **kwargs):
        #_log.info("Got new data: {}".format(kwargs["data"]))
        data = kwargs.get("data")
        self.tokens.append(data)
        return len(self.tokens)

    action_priority = (send, )
    
    requires=['kappa']