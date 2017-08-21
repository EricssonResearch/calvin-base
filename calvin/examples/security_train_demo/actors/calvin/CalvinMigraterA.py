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
from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)

class CalvinMigraterA(Actor):

    """
    Migrate actor(s) in app according to argument defined
    deployment informations
    control_uri: a runtime
    deploy_info: {<key string as received on key port>: <any deploy info>, ...}

    Inputs:
      control_uri: a control_uri instead of as argument (connect Void actor if using argument)
      app_id: app_id (either string or dict with "application_id" key)
      key : key to activate a predefined deploy info
      status: Connected from HTTPPost Actor
      header: Connected from HTTPPost Actor
      data : Connected from HTTPPost Actor
    Outputs:
      done : (key, True/False)
      URL : Connected to HTTPPost Actor
      params : Connected to HTTPPost Actor
      header: Connected to HTTPPost Actor
      data: Connected to HTTPPost Actor
    """

    @manage([])
    def init(self, deploy_info, control_uri=None):
        self.control_uri = control_uri
        self.use(requirement='calvinsys.native.python-json', shorthand='json')
        self.deploy_info = {a: self['json'].dumps({'deploy_info': d, "move": False}) for a, d in deploy_info.iteritems()}
        self.app_id = None
        self.last_keys = []

    @condition(['control_uri'], [])
    def new_control_uri(self, control_uri):
        if control_uri:
            self.control_uri = control_uri

    def exception_handler(self, action, args, context):
        # Ignore any exceptions

    @condition(['app_id'], [])
    def got_app_id(self, app_id):
        """ Got app id. If changed client must make sure that all request responses are recieved first"""
        if isinstance(app_id, dict):
            try:
                self.app_id = app_id["application_id"]
            except:
                pass
        elif isinstance(app_id, basestring):
            self.app_id = app_id
        elif app_id is None:
            self.app_id = None
        # Just continue waiting for valid app id if not correctly formatted

    def guard_migrate(self, key):
        if self.app_id is None or self.control_uri is None:
            return False
        return key in self.deploy_info

    @condition(['key'], ['URL', 'data', 'params', 'header'])
    @guard(guard_migrate)
    def migrate(self, key):
        self.last_keys.append(key)
        _log.info("MIGRATE %s\n%s" % (self.control_uri + "/application/" + self.app_id + "/migrate", self.deploy_info[key]))
        return (production=(self.control_uri + "/application/" + self.app_id + "/migrate",
                                        self.deploy_info[key], {}, {}))

    @condition(['key'], ['done'])
    @guard(lambda self, key: key not in self.deploy_info)
    def wrong_key(self, key):
        _log.info("MIGRATE WRONG KEY %s" % key)
        return (production=([key, False],))

    @condition(['status', 'header', 'data'], ['done'])
    def migrated(self, status, header, data):
        response = status >= 200 and status < 300
        key = self.last_keys.pop(0)
        _log.info("MIGRATED %s response %d" % (key, status))
        return (production=([key, response],))

    action_priority = (migrate, migrated, wrong_key, got_app_id, new_control_uri)
    requires =  ['calvinsys.native.python-json']
