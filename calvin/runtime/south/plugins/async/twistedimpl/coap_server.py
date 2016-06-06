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
from twisted.internet import defer

from calvin.runtime.south.plugins.async.twistedimpl.coap import coap
from calvin.runtime.south.plugins.async.twistedimpl.coap import resource
from calvin.runtime.south.plugins.async.twistedimpl.coap import error

from urlparse import urlparse

from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCBClass
from calvin.utilities.calvin_callback import CalvinCB

import time

_log = get_logger(__name__)

class CalvinResource(CalvinCBClass, resource.CoAPResource):
    def __init__(self, callbacks=None, data=''):
        super(CalvinResource, self).__init__(callbacks, callback_valid_names=['data',])
        self._callbacks = callbacks  
        self.data = data
        self.visible = True
        self.children = {}
	self.params = {}
	self.observers = {}

        self.addParam(resource.LinkParam("title", "Calvin data resource"))

    def render_GET(self, request):
	response = coap.Message(code=coap.CONTENT, payload=self.data)
        return defer.succeed(response)

    def render_PUT(self, request):
	self.data = request.payload
	response = coap.Message(code=coap.CHANGED, payload=self.data)
        return defer.succeed(response)

    def render_POST(self, request):
	self.data = request.payload
        self._callback_execute('data', self.data, request.remote)

	response = coap.Message(code=coap.CHANGED, payload=self.data)
        return defer.succeed(response)

    def render_DELETE(self, request):
	self.data = None #Note: does not actually remove resource. data==None implies nonexistence of resource.
	response = coap.Message(code=coap.DELETED)
        return defer.succeed(response)
    
    def getChild(self, path, request):
	if len(request.postpath) == 0 and (request.code==coap.POST or request.code==coap.PUT):
	    #dynamically create new CalvinResource
	    newres = CalvinResource(callbacks=self._callbacks, data=request.payload)
	    self.putChild(path, newres)
	    return newres
	raise error.NoResource

class CoreResource(resource.CoAPResource):
    def __init__(self, root):
	resource.CoAPResource.__init__(self)
	self.root = root
 
    def render_GET(self, request):
	data = []
	self.root.generateResourceList(data, "")
	payload = ','.join(data)
	print payload
	response = coap.Message(code=coap.CONTENT, payload = payload)
	response.opt.content_format = coap.media_types_rev['application/link-format']
	return defer.succeed(response)

def generateCoAP(callbacks):
    root = CalvinResource(callbacks=callbacks)
    well_known = CalvinResource()
    root.putChild('.well-known', well_known)
    core = CoreResource(root)
    well_known.putChild('core',core)
	
    endpoint = resource.Endpoint(root)	
    return coap.Coap(endpoint)

class CoAPServer(CalvinCBClass):
    def __init__(self, serverport=5683, callbacks=None):
	self._serverport = serverport
        self._callbacks = callbacks
	self._received_data = []

	proto_callbacks = {'data': [CalvinCB(self._new_data)]}
        self._proto = generateCoAP(proto_callbacks)
	
	reactor.listenUDP(self._serverport, self._proto)

    def _started(self, port):
        self._port = port
        self._callback_execute('server_started', self, self._port)

    def _stopped(self):
        self._port = None
        self._callback_execute('server_stopped', self)
        # TODO: remove this ?
        # self._transport.callback_register('peer_connected', CalvinCB(self._peer_connected))

    def start(self):
	_log.info("start server: %s" % time.clock())
	pass
        # These should come from us
        #self.callback_register('server_started', CalvinCB(self._started))
        #self.callback_register('server_stopped', CalvinCB(self._stopped))

    def stop(self):
        pass

    def _new_data(self, data, remote):
        self._received_data.append({"data":data, "remote":remote})

    def data_available(self):
        return len(self._received_data) > 0

    def get_data(self):
        dataobj = self._received_data.pop(0)
        return "%s:%s, %s" % (dataobj["remote"][0], dataobj["remote"][1], dataobj["data"])

