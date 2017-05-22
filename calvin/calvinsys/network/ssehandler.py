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

# FIXME: Stray line below?
from calvin.runtime.south.plugins.async import sse_event_source
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class SSEHandler(object):
    def __init__(self, node, actor):
        super(SSEHandler, self).__init__()
        self.node   = node
        self.server = None
        self._actor = actor

    def start(self, port):
        print "START", port
        self.server = sse_event_source.EventSource(port)
        # return self.server

    def stop(self):
        print "STOP", self
        # self.server.stop()

    def broadcast(self, payload):
        # print "BROADCAST", self.server._eventsource, payload
        self.server.broadcast(payload)


def register(node, actor):
    """
        Called when the system object is first created.
    """
    return SSEHandler(node, actor)
