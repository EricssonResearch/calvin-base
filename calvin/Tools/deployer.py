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

from calvin.utilities.calvinlogger import get_logger
from calvin.requests.request_handler import RequestHandler

_log = get_logger(__name__)


class Deployer(object):

    """
    Deprecated!
    Thin layer to support legacy users.
    New users should use the control REST API or the RequestHandler.deploy_application or RequestHandler.deploy_app_info
    Deploys an application to a runtime.
    """

    def __init__(self, runtime, deployable, credentials=None, verify=True, request_handler=None):
        super(Deployer, self).__init__()
        self.runtime = runtime
        self.deployable = deployable
        self.credentials = credentials
        self.actor_map = {}
        self.app_id = None
        self.verify = verify
        self.request_handler = request_handler if request_handler else RequestHandler()
        if "name" in self.deployable:
            self.name = self.deployable["name"]
        else:
            self.name = None

    def deploy(self):
        """
        Ask a runtime to instantiate actors and link them together.
        """
        if not self.deployable['valid']:
            import json
            print(json.dumps(self.deployable, indent=2, default=str))
            raise Exception("Deploy information is not valid")

        result = self.request_handler.deploy_app_info(self.runtime, self.name, self.deployable, check=self.verify)
        self.app_id = result['application_id']
        self.actor_map = result['actor_map']
        self.replication_map = result.get('replication_map', {})
        return self.app_id

    def destroy(self):
        return self.request_handler.delete_application(self.runtime, self.app_id)
