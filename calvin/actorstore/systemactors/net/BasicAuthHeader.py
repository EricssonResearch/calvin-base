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

from calvin.actor.actor import Actor, ActionResult, manage, condition


class BasicAuthHeader(Actor):
    """
    Generate Basic Authorization header from username/password

    Inputs:
      credential: JSon with values for "username" and "password"
    Outputs:
      header : Authorization header
    """

    @manage()
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.use('calvinsys.native.python-base64', shorthand="base64")

    @condition(['credential'], ['header'])
    def authorization_header(self, credential):
        auth = "Basic " + self['base64'].b64encode("%s:%s" % (credential['username'], credential['password']))
        header = {'Authorization': auth}
        return ActionResult(production=(header,))

    action_priority = (authorization_header,)
    requires = ['calvinsys.native.python-base64']

    test_set = [
        {
            'in': {'credential': [{"username": "root", "password": "pass"}]},
            'out': {'header': [{"Authorization": "Basic cm9vdDpwYXNz"}]}
        }
    ]
