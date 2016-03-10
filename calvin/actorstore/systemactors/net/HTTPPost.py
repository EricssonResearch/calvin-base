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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class HTTPPost(Actor):
    """
    POST data to URL, retrieving reply

    Input:
      URL : URL to post to
      params : Optional parameters to request as a JSON dictionary
      header: JSON dictionary with headers to include in request
      data : data to send to URL
    Output:
      status: 200/404/whatever
      header: JSON dictionary of incoming headers
      data : body of request
    """

    @manage()
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.request = None
        self.received_headers = False
        self.use('calvinsys.network.httpclienthandler', shorthand='http')
        self.use('calvinsys.native.python-json', shorthand='json')

    @condition(action_input=['URL', 'params', 'header', 'data'])
    @guard(lambda self, url, params, header, data: self.request is None)
    def new_request(self, url, params, header, data):
        url = url.encode('ascii', 'ignore')
        self.request = self['http'].post(url, params, header, data)
        return ActionResult()

    @condition(action_output=['status', 'header'])
    @guard(lambda self: self.request and not self.received_headers and self['http'].received_headers(self.request))
    def handle_headers(self):
        self.received_headers = True
        status = self['http'].status(self.request)
        headers = self['http'].headers(self.request)
        return ActionResult(production=(status, headers))

    @condition(action_output=['data'])
    @guard(lambda self: self.received_headers and self['http'].received_body(self.request))
    def handle_body(self):
        body = self['http'].body(self.request)
        self.received_headers = False
        self['http'].finalize(self.request)
        self.request = None
        return ActionResult(production=(body,))

    action_priority = (handle_body, handle_headers, new_request)
    requires = ['calvinsys.network.httpclienthandler', 'calvinsys.native.python-json']
