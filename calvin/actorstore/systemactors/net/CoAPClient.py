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

class CoAPClient(Actor):
    """
    GET, POST, PUT or DELETE data to URL, retrieving reply

    Input:
      command : type of CoAP request. Either GET, POST, PUT or DELETE
      mtype : type of CoAP message. Either CON or NON
      url : URL to post
      options: JSON dictionary of CoAP options
      data : data to send to URL. Not used for GET and DELETE.
    Output:
      status: CoAP response code
      data : body of request
    """

    @manage()
    def init(self, dtls=False, objectsecurity=False, oscontext=''):
        self.setup(dtls, objectsecurity, oscontext)

    def did_migrate(self):
        self.setup()

    def setup(self, dtls=False, objectsecurity=False, oscontext=''):
        self.reset_request()
	if not dtls and not objectsecurity:
            self.use('calvinsys.network.coapclienthandler', shorthand='coap')
        elif dtls and not objectsecurity:
            self.use('calvinsys.network.coapdtlsclienthandler', shorthand='coap')
        elif not dtls and objectsecurity:
            self.use('calvinsys.network.coaposclienthandler', shorthand='coap')
        elif dtls and objectsecurity:
            self.use('calvinsys.network.coapdtlsosclienthandler', shorthand='coap')
	
	if objectsecurity:
	    self['coap'].setSecurityContext(oscontext)

    def reset_request(self):
        self.request = None

    @condition(action_input=['command', 'mtype', 'url', 'options'])
    @guard(lambda self, command, mtype, url, options: self.request is None and (command == 'GET' or command == 'DELETE') and (mtype == 'CON' or mtype == 'NON'))
    def new_GETDELETErequest(self, command, mtype, url, options):
	if command == 'GET':
	    self.request = self['coap'].get(mtype, url, options)
	elif command == 'DELETE':
	    self.request = self['coap'].delete(mtype, url, options)
	
        return ActionResult()

    @condition(action_input=['command', 'mtype', 'url', 'options', 'data'])
    @guard(lambda self, command, mtype, url, options, data: self.request is None and (command == 'POST' or command == 'PUT') and (mtype == 'CON' or mtype == 'NON'))
    def new_POSTPUTrequest(self, command, mtype, url, options, data):
	if command == 'PUT':
	    self.request = self['coap'].put(mtype, url, options, str(data))
	elif command == 'POST':
	    self.request = self['coap'].post(mtype, url, options, str(data))
	
        return ActionResult()

    @condition(action_output=['status', 'data'])
    @guard(lambda self: self.request and self['coap'].received_response(self.request))
    def handle_response(self):
        status = self['coap'].status(self.request)
	data = self['coap'].data(self.request)
	
        self.reset_request()	
	
        return ActionResult(production=(status, data))

    action_priority = (handle_response, new_GETDELETErequest, new_POSTPUTrequest)
    requires = ['calvinsys.network.coapclienthandler', 'calvinsys.network.coapdtlsclienthandler', 'calvinsys.network.coaposclienthandler', 'calvinsys.network.coapdtlsosclienthandler']
