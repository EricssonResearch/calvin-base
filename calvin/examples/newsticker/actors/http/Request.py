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

# encoding: utf-8

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
import requests
import json

class Request(Actor):

    """
    Make an HTTP GET request and return the response.

    FIXME: Rewrite this using Calvinsys

    Inputs:
      URL:    A URL for the request formatted as: https://foo.bar.com/some/data
      params: Parameters formatted as: "?foo=bar;baz=0" or "" for no params
      header: Additional header lines formatted as: "Foo: \\"BAR\\"\\r\\n\\r\\nBaz: 0" or "" for no extra header lines
    Outputs:
      status: HTTP status 200/400/404/501/etc.
      data :  Server response
      header: Response header
    """


    @manage()
    def init(self):
        pass

    @condition(['URL', 'params', 'header'], ['status', 'data', 'header'])
    def request(self, url, params, header):
        r = requests.get(url.encode('utf-8'), params=params, headers=header)
        status = r.status_code
        data = json.loads(r.text) if status == 200 else []
        header = dict(r.headers)
        return ActionResult(production=(status, data, header))

    action_priority = (request, )

