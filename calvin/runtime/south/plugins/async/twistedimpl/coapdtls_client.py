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

from twisted.internet import reactor
from twisted.internet.defer import Deferred

from calvin.runtime.south.plugins.async.twistedimpl.coap import coap
from calvin.runtime.south.plugins.async.twistedimpl.coap import resource

from calvin.runtime.south.plugins.async.twistedimpl import dtls_port

from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCBClass

from urlparse import urlparse

_log = get_logger(__name__)

# Object to store CoAP response in.
class CoAPResponse(object):
    def __init__(self):
        self._response = {}

    def parse_response(self, response):
	self._response = {}
	self._response['status'] = coap.responses[response.code]
	self._response['data'] = response.payload

    def status(self):
	return self._response.get('status', None)

    def data(self):
	return self._response.get('data', None)

class CoAPClient(CalvinCBClass):

    def __init__(self, callbacks=None):
        super(CoAPClient, self).__init__(callbacks)
	self._proto = coap.Coap(resource.Endpoint(None))
	self.url = None
	

    def request(self, command, mtype, url, options, data):
	if url is not self.url:
            self.url = url
            urlobject = urlparse(url)
	    self._proto = coap.Coap(resource.Endpoint(None))
	    self.transport = dtls_port.DTLSClientPort(0, proto=self._proto, reactor=reactor, address=(urlobject.hostname, urlobject.port))

        if mtype == 'NON':
	    coapmtype = coap.NON
	elif mtype == 'CON':
	    coapmtype = coap.CON

	if command == 'GET':
	    request = request = coap.Message(mtype=coapmtype, code=coap.GET)
	elif command == 'PUT':
	    request = request = coap.Message(mtype=coapmtype, code=coap.PUT, payload=data)
	elif command == 'POST':
	    request = request = coap.Message(mtype=coapmtype, code=coap.POST, payload=data)
	elif command == 'DELETE':
	    request = request = coap.Message(mtype=coapmtype, code=coap.DELETE)
	return self._send_request(request, url, options)
    
    def _receive_response(self, response, responseObject):
	responseObject.parse_response(response)
	self._callback_execute('receive-response', responseObject)

    def _send_request(self, request, url, options):
	urlobject = urlparse(url)
	
	#uri_path contains the URI of the resource on the server.
	uripath = urlobject.path.split('/')
	if uripath[0] == '':
	    uripath = uripath[1:]
	request.opt.uri_path = uripath
	
	#deal with options. Valid option keys: etag, observe, location_path, uri_path, content_format, uri_query, accept, block2 and block1.
	for option in options:
            if type(options[option]) is unicode:
	        setattr(request.opt, option, str(options[option]))
            else:
                setattr(request.opt, option, options[option])
        
        request.opt.content_format = coap.media_types_rev['text/plain']	
	request.remote = (urlobject.hostname, urlobject.port)

	# responseObject acts as handle for the CoAP response. When a response is received, it will be stored in this object. The actor can then access the response through this object.
	deferred = self._proto.request(request)
	responseObject = CoAPResponse()
	deferred.addCallback(self._receive_response, responseObject)
	return responseObject
