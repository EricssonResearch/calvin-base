# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.actor.actor import Actor, manage, condition, guard
from calvin.runtime.north.calvin_token import ExceptionToken

import json

class CalvinDeployerA(Actor):

    """
    Deploys a calvin script to a runtime

    Inputs:
      control_uri: a control_uri instead of as argument (connect Void actor if using argument)
      name: deployed apps name as string
      script : Script as text
      deploy_info: deploy_info as text or None
      sec_credentials: username and password or None
      status: Connected from HTTPPost Actor
      header: Connected from HTTPPost Actor
      data : Connected from HTTPPost Actor
    Outputs:
      app_info : Application id and placement in dictionary or exception token when failed
      URL : Connected to HTTPPost Actor
      params : Connected to HTTPPost Actor
      header: Connected to HTTPPost Actor
      data: Connected to HTTPPost Actor
    """

    @manage([])
    def init(self, control_uri=None):
        self.control_uri = control_uri
        self.use(requirement='calvinsys.native.python-json', shorthand='json')

    @condition(['control_uri'], [])
    def new_control_uri(self, control_uri):
        if control_uri:
            self.control_uri = control_uri

    def exception_handler(self, action, args, context):
        # Ignore any exceptions

    @condition(['name', 'script', 'deploy_info','sec_credentials'], ['URL', 'data', 'params', 'header'])
    @guard(lambda self, name, script, deploy_info, sec_credentials: self.control_uri is not None)
    def deploy(self, name, script, deploy_info, sec_credentials):
        print "name:%s     script:%s    sec_credentials:%s "% (name, script, sec_credentials)
#        body = self['json'].dumps({'script': script, 'name': name, 'deploy_info':deploy_info, 'check': False})
        body = self['json'].dumps({'script': script, 'name': name,
                                    'deploy_info':deploy_info, 'check': False, 
                                    'sec_credentials':sec_credentials})
        return (production=(self.control_uri + "/deploy", body, {}, {}))

    @condition(['status', 'header', 'data'], ['app_info'])
    def deployed(self, status, header, data):
        try:
            response = self['json'].loads(data)
        except:
            response = None
        if status < 200 or status >= 300:
            # Failed deployed
            response = ExceptionToken(value=status)
        return (production=(response,))

    action_priority = (deployed, deploy, new_control_uri)
    requires =  ['calvinsys.native.python-json']
