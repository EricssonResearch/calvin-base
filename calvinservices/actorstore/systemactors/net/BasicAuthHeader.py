# -*- coding: utf-8 -*-

# Copyright (c) 2015-17 Ericsson AB
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

from calvin.actor.actor import Actor, manage, condition, calvinlib


class BasicAuthHeader(Actor):
    """
    documentation:
    - Generate Basic Authorization header from username/password
    ports:
    - direction: in
      help: JSon with values for "username" and "password"
      name: credential
    - direction: out
      help: Authorization header
      name: header
    requires:
    - base64
    """

    @manage()
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.base64 = calvinlib.use('base64')

    @condition(['credential'], ['header'])
    def authorization_header(self, credential):
        auth_str = "{username}:{password}".format(**credential)
        b64_auth_str = self.base64.encode(auth_str.encode('utf-8'))
        auth = "Basic " + b64_auth_str
        header = {'Authorization': auth}
        return (header,)

    action_priority = (authorization_header,)
    


    test_set = [
        {
            'inports': {'credential': [{"username": "root", "password": "pass"}]},
            'outports': {'header': [{"Authorization": "Basic cm9vdDpwYXNz"}]}
        }
    ]
