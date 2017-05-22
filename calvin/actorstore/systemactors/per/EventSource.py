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

# encoding: utf-8

from calvin.actor.actor import Actor, manage, condition
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken
from calvin.runtime.south.plugins.async import sse_event_source as sse
import json

class EventSource(Actor):
    """
    Summary

    Detailed information

    Inputs:
      token : a token to be sent to clients
    """

    @manage(['port'])
    def init(self, port):
        self.port = port
        self.setup()

    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        if self.publisher:
            self.publisher.stop()
            self.publisher = None

    def will_end(self):
        if self.publisher:
            self.publisher.stop()

    def setup(self):
        self.use('calvinsys.network.ssehandler', shorthand='sse')
        self.publisher = self['sse']
        self.publisher.start(self.port)

    @condition(action_input=["token"])
    def broadcast(self, tok):
        s = json.dumps(tok)
        self.publisher.broadcast(s)

    action_priority = (broadcast, )
    requires = ['calvinsys.network.ssehandler']
