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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class IPCamera(Actor):
    """
    When input trigger goes high, fetch image from given device.

    Inputs:
      trigger: binary input
    Outputs:
      image: generated image
      status: 200/404/whatever
    """

    @manage(exclude=['ip', 'credentials'])
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.request = None
        self.reset_request()
        self.use('calvinsys.network.httpclienthandler', shorthand='http')
        self.use('calvinsys.native.python-base64', shorthand="base64")
        self.use('calvinsys.attribute.private', shorthand="attr")
        # Requires an IP address and user credentials
        # Example:
        # self.ip = "192.168.1.4"
        # self.credentials = {"username": "root", "password": "pass"}
        self.ip = self['attr'].get("/media/ip_camera/ip").encode('utf8')
        self.credentials = {
            "username": self['attr'].get("/media/ip_camera/username"), 
            "password": self['attr'].get("/media/ip_camera/password")
        }

    def reset_request(self):
        self.received_status = False
        if self.request:
            self['http'].finalize(self.request)
            self.request = None
        
    @condition(action_input=['trigger'])
    @guard(lambda self, trigger: self.ip and self.credentials and self.request is None and trigger)
    def new_request(self, trigger):
        url = "http://" + self.ip + "/axis-cgi/jpg/image.cgi"
        auth = "Basic " + self['base64'].b64encode("%s:%s" % (self.credentials['username'], self.credentials['password']))
        header = {'Authorization': auth}
        params = {}
        self.request = self['http'].get(url, params, header)
        return ActionResult()

    @condition(action_output=['status'])
    @guard(lambda self: self.request and not self.received_status and self['http'].received_headers(self.request))
    def handle_headers(self):
        status = self['http'].status(self.request)
        self.received_status = status
        return ActionResult(production=(status,))

    @condition(action_output=['image'])
    @guard(lambda self: self.request and self.received_status == 200 and self['http'].received_body(self.request))
    def handle_body(self):
        body = self['http'].body(self.request)
        image = self['base64'].b64encode(body)
        self.reset_request()
        return ActionResult(production=(image,))

    @condition()
    @guard(lambda self: self.request and self.received_status and self.received_status != 200)
    def handle_empty_body(self):
        self.reset_request()
        return ActionResult()

    action_priority = (handle_body, handle_empty_body, handle_headers, new_request)
    requires = ['calvinsys.network.httpclienthandler', 'calvinsys.native.python-base64', "calvinsys.attribute.private"]
