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

from calvin.runtime.south.plugins.async import http_client
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class HTTPClientHandler(object):
    def __init__(self, node, actor):
        _log.info("Started HTTPClientHandler")
        self._actor = actor
        self._node = node
        callbacks = {'receive-headers': [CalvinCB(self._receive_headers)],
                     'receive-body': [CalvinCB(self._receive_body)]}
        self._client = http_client.HTTPClient(callbacks)
        self._requests = {}

    def _issue_request(self, cmd, url, params, headers, data):
        handle = "%s:%s:%s" % (self._actor.id, cmd, url)
        if not headers.get("User-Agent", None):
            headers["User-Agent"] = "Calvin-Base"
        self._requests[handle] = self._client.request(cmd, url, params, headers, data)
        return handle

    def post(self, url, params=None, headers=None, data=None):
        return self._issue_request('POST', url, params, headers, data)

    def put(self, url, params=None, headers=None, data=None):
        return self._issue_request('PUT', url, params, headers, data)

    def get(self, url, params=None, headers=None):
        return self._issue_request('GET', url, params, headers, None)

    def _receive_headers(self, dummy=None):
        self._node.sched.trigger_loop()

    def _receive_body(self, dummy=None):
        self._node.sched.trigger_loop()

    def received_headers(self, handle):
        return self._requests[handle].headers() is not None

    def received_body(self, handle):
        body = self._requests[handle].body()
        return bool(body)

    def received_empty_body(self, handle):
        body = self._requests[handle].body()
        return body is not None and not bool(body)

    def headers(self, handle):
        return self._requests[handle].headers()

    def body(self, handle):
        return self._requests[handle].body()

    def status(self, handle):
        return self._requests[handle].status()

    def phrase(self, handle):
        return self._requests[handle].phrase()

    def finalize(self, handle):
        self._requests.pop(handle, None)

def register(node, actor):
    """
        Fetch a new handler
    """
    return HTTPClientHandler(node, actor)
