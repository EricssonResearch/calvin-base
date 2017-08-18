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

# from twisted.internet.task import react
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
try:
    from twisted.internet.ssl import ClientContextFactory
    HAS_OPENSSL = True
except:
    # Probably no OpenSSL available.
    HAS_OPENSSL = False

from twisted.web.client import FileBodyProducer
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol

from StringIO import StringIO
from urllib import urlencode

from calvin.utilities.calvin_callback import CalvinCBClass

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


class HTTPRequest(object):
    def __init__(self):
        self._response = {}

    def parse_headers(self, response):
        self._response['version'] = "%s/%d.%d" % (response.version)
        self._response['status'] = response.code
        self._response['phrase'] = response.phrase
        self._response['headers'] = {}
        for hdr, val in response.headers.getAllRawHeaders():
            self._response['headers'][hdr.lower()] = val[0] if isinstance(val, list) and len(val) > 0 else val

    def parse_body(self, body):
        self._response['body'] = body

    def parse_error(self, err_msg):
        self._response['error'] = err_msg
        

    def error(self):
        return self._response.get('error', None)
        
    def body(self):
        return self._response.get('body', None)

    def headers(self):
        return self._response.get('headers', None)

    def status(self):
        return self._response.get('status', None)

    def version(self):
        return self._response.get('version', None)

    def phrase(self):
        return self._response.get('phrase', None)


def encode_params(params):
    if params:
        return "?" + urlencode(params)
    return ""


def encode_headers(headers):
    twisted_headers = Headers()
    for k, v in headers.items():
        key = k.encode('ascii', 'ignore')
        val = v.encode('ascii', 'ignore')
        twisted_headers.addRawHeader(key, val)
    return twisted_headers


def encode_body(data):
    if not data:
        return None
    if not isinstance(data, basestring):
        return None
    ascii_data = data.encode('ascii', 'ignore')
    print "ascii_data=",ascii_data
    return FileBodyProducer(StringIO(ascii_data))


class BodyReader(Protocol):

    def __init__(self, deferred, cb, request):
        self.deferred = deferred
        self.data = ""
        self.cb = cb
        self.request = request

    def dataReceived(self, bytes):
        self.data += bytes

    def connectionLost(self, reason):
        self.deferred.callback(None)
        self.cb(self.data, self.request)


class HTTPClient(CalvinCBClass):

    def create_agent(self):
        if HAS_OPENSSL:
            class WebClientContextFactory(ClientContextFactory):
                """TODO: enable certificate verification, hostname checking"""
                def getContext(self, hostname, port):
                    return ClientContextFactory.getContext(self)
            return Agent(reactor, WebClientContextFactory())
        else:
            return Agent(reactor)

    def __init__(self, callbacks=None):
        super(HTTPClient, self).__init__(callbacks)
        self._agent = self.create_agent()

    def _receive_headers(self, response, request):
        request.parse_headers(response)
        self._callback_execute('receive-headers', request)
        finished = Deferred()
        response.deliverBody(BodyReader(finished, self._receive_body, request))
        return finished

    def _receive_body(self, response, request):
        request.parse_body(response)
        self._callback_execute('receive-body', request)

    def _receive_error(self, reason, request):
        request.parse_error(reason.getErrorMessage())
        self._callback_execute('receive-headers', request)
            

    def request(self, command, url, params, headers, data):
        url += encode_params(params)
        twisted_headers = encode_headers(headers)
	print "ENglund, pre-body:",data
        body = encode_body(data)
	print "ENglund, post-body:",body
        deferred = self._agent.request(command, url, headers=twisted_headers, bodyProducer=body)
        request = HTTPRequest()
        deferred.addCallback(self._receive_headers, request)
        deferred.addErrback(self._receive_error, request)
        return request
