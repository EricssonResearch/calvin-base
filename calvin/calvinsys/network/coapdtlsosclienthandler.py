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

from calvin.runtime.south.plugins.async.twistedimpl.coapdtlsos_client import CoAPClient

from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class CoAPClientHandler(object):
    def __init__(self, node, actor):
        self._actor = actor
        self._node = node
        callbacks = {'receive-response': [CalvinCB(self._receive_response)]}

        self._client = CoAPClient(callbacks)
        self._requests = {}

    def setSecurityContext(self, securitycontext):
	self._client.setSecurityContext(securitycontext)

    def _issue_request(self, cmd, mtype, url, options=None, data=None):
        handle = "%s:%s:%s" % (self._actor.id, cmd, url)
        self._requests[handle] = self._client.request(cmd, mtype, url, options, data)
        return handle

    def post(self, mtype, url, options=None, data=None):
        return self._issue_request('POST', mtype, url, options, data)

    def put(self, mtype, url, options=None, data=None):
        return self._issue_request('PUT', mtype, url, options, data)

    def get(self, mtype, url, options=None):
        return self._issue_request('GET', mtype, url, options=options)

    def delete(self, mtype, url, options=None):
        return self._issue_request('DELETE', mtype, url, options=options)

    def _receive_response(self, dummy=None):
        self._node.sched.trigger_loop()

    def received_response(self, handle):
        return self._requests[handle].status() is not None

    def data(self, handle):
        return self._requests[handle].data()

    def status(self, handle):
        return self._requests[handle].status()

def register(node, actor):
    """
        Fetch a new handler
    """
    return CoAPClientHandler(node, actor)
