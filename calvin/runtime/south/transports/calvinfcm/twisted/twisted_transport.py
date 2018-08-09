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

import json
import inspect
import time
import traceback
import base64
import pdb
import struct

from calvin.utilities.calvin_callback import CalvinCB, CalvinCBClass
from calvin.utilities import calvinlogger
from calvin.runtime.south.transports.lib.twisted import base_transport
from calvin.runtime.south.transports import base_transport as calvin_base_transport
from calvin.utilities import calvinconfig
from twisted.protocols.basic import Int32StringReceiver

from twisted.internet import protocol, reactor, ssl
from twisted.names.srvconnect import SRVConnector
from twisted.words.protocols.jabber import client
from twisted.words.xish import xmlstream as xishxmlstream
from twisted.words.protocols.jabber import xmlstream

from twisted.words.protocols.jabber.jid import JID

_log = calvinlogger.get_logger(__name__)

_CONF = calvinconfig.get()

def create_uri(sender_id, token):
    return "calvinfcm://%s:%s" % (sender_id, token)

class CalvinXMLStreamProtocol(CalvinCBClass, xmlstream.XmlStream):

    def __init__(self, *args, **kvargs):
        self._authenticator = args[0]
        self._callbacks = args[1]
        self._uri = args[2]
        self._server = args[3]
        xmlstream.XmlStream.__init__(self, self._authenticator)
        CalvinCBClass.__init__(self, self._callbacks)
        self.counter = 0

    def send(self, obj):
        return super(CalvinXMLStreamProtocol, self).send(obj)

    def sendCalvinMsg(self, to, data, msgType="payload"):
        toSend ="<message id=\"\"><gcm xmlns=\"google:mobile:data\">%s</gcm></message>"
        # Payload should be base64 encoded
        # Add 4 byte data length before data
        dataSize = len(data)
        dlen = struct.pack("cccc"+str(dataSize)+"s", chr(dataSize >> 24 & 0xFF), chr(dataSize >> 16 & 0xFF), chr(dataSize >> 8 & 0xFF), chr(dataSize & 0xFF), data)
        data = base64.b64encode(dlen)
        d = {
                "to": to,
                "message_id": "UPID%s%d" % (str(time.time()), self.counter),
                "priority": "high",
                "data": {
                        "msg_type": msgType,
                        "payload": data
                    },
                "time_to_live": 600
                }
        self.counter = self.counter + 1
        self.send(toSend % str(json.dumps(d)))

    def dataReceived(self, data):
        return super(CalvinXMLStreamProtocol, self).dataReceived(data)

    def connectionLost(self, reason):
        self._callback_execute('disconnected', reason)
        valid_names = self.callback_valid_names()
        ids = []
        for name in valid_names:
            cbs = self.get_callbacks_by_name(name)
            for cb_id in cbs:
                _log.debug("Removing cbs: %s" % cb_id)
                ids.append(cb_id)

        for cb_id in ids:
            self.callback_unregister(cb_id)

        #return super(CalvinXMLStreamProtocol, self).connectionLost(reason)

    def onElement(self, element):
        # Child of root element received
        for e in element.elements():
            if e and e.name == "gcm" and e.uri == "google:mobile:data":
                (calvinMsg, payload) = self.handleJsonPayload(str(e))
                break
        return super(CalvinXMLStreamProtocol, self).onElement(element)

    def sendAck(self, messageId, regId):
        ackData = {"to": regId, "message_id": messageId, "message_type": "ack"}
        return self.send(self.getFCMDataWrapper() % json.dumps(ackData))

    def getFCMDataWrapper(self):
        return "<message id=\"\"><gcm xmlns=\"google:mobile:data\"> %s </gcm></message>"

    def handleJsonPayload(self, raw_data):
        data = json.loads(raw_data)
        messageId = data["message_id"]
        try:
            # Check if we got an ACK message
            if "message_type" in data and data["message_type"] == "ack":
                return (False, None)
            elif "category" in data and "message_id" in data and "data" in data:
                self.sendAck(messageId, self._uri.hostname)
                # We have a payload fcm message
                payload = data["data"]
                msg_type = payload["msg_type"]
                if msg_type == "set_connect":
                    if payload["connect"] == "1":
                        self._server._connected(self, data["from"])
                    else:
                        self._callback_execute("disconnect")
                elif msg_type == "payload":
                    self._callback_execute("data", data)
        except Exception as e:
            traceback.print_exc()

        return (True, None)

class CalvinXMLStreamFactory(CalvinCBClass, xishxmlstream.XmlStreamFactory):
    protocol = CalvinXMLStreamProtocol
    def __init__(self, authenticator, callbacks, server, uri=None):
        xishxmlstream.XmlStreamFactory.__init__(self, authenticator, callbacks, uri, server)
        self._authenticator = authenticator
        self._callbacks = callbacks

    def buildProtocol(self, addr):
        self.resetDelay()
        self.proto = xishxmlstream.XmlStreamFactoryMixin.buildProtocol(self, addr)
        return self.proto

# Server
class TwistedCalvinTransport(base_transport.CalvinServerBase):

    def __init__(self, iface='', node_name=None, port=0, callbacks=None, uri=None, *args, **kwargs):
        super(TwistedCalvinTransport, self).__init__(callbacks=callbacks)
        self._uri = calvin_base_transport.URI(uri)
        self._jid = self._uri.hostname
        self._iface = iface
        self._node_name=node_name
        self._port = self._uri.port
        self._addr = None
        self._tcp_server = None
        self._callbacks = callbacks
        self._runtime_credentials = None
        self.connected = False

    def start(self):
        jid = JID(str(self._jid) + "@gcm.googleapis.com")

        secret = _CONF.get(None, 'fcm_server_secret')
        if secret == None:
            _log.error("No secret specified")
            return
        authenticator = client.XMPPAuthenticator(jid, secret)

        callbacks = {'connected': [CalvinCB(self._connected)]}
        xmppfactory = CalvinXMLStreamFactory(authenticator, callbacks, self, self._uri)
        xmppfactory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)

        self.protocol_factory = xmppfactory

        cf = ssl.ClientContextFactory()
        reactor.connectSSL("gcm-preprod.googleapis.com", 5236, xmppfactory, cf)

    def stop(self):
        traceback.print_stack()

    def authenticated(self, xs):
        _log.info("Authenticated with FCM server")
        self._callback_execute('server_started', self._port)

    def stop(self):
        _log.debug("Stopping fcm server")

    def is_listening(self):
        return True

    def _connected(self, proto, token):
        self._callback_execute('client_connected', create_uri(self._jid, token), proto)

# Client
class TwistedCalvinTransportClient(base_transport.CalvinTransportBase):
    def __init__(self, host, port, callbacks=None, proto=None, node_name=None, server_node_name=None, *args, **kwargs):
        super(TwistedCalvinTransportClient, self).__init__(host, port, callbacks=callbacks)
        self._jid = host
        self._token = port
        self._proto = proto
        self._uri = proto._uri
        self._factory = None
        self._node_name = node_name
        self._server_node_name=server_node_name
        self._runtime_credentials = None
        self._is_connected = False
        if proto:
            proto.callback_register('connected', CalvinCB(self._connected))
            proto.callback_register('disconnected', CalvinCB(self._disconnected))
            proto.callback_register('data', CalvinCB(self._data))

        self._callbacks = callbacks
        self.sendConnected()

    def is_connected(self):
        return self._is_connected

    def sendConnected(self):
        d = {
                "connected": 1
                }
        self._proto.sendCalvinMsg(self._token, json.dumps(d), msgType="set_connect")

    def join(self):
        raise NotImplementedError

    def _connected(self, proto, token):
        self._is_connected = True
        self._callback_execute('connected')

    def _disconnected(self, reason):
        self._callback_execute('disconnected', reason)
        self._is_connected = False

    def _data(self, data):
        try:
            sender = data["from"]
            if sender == self._token: # MUX
                payload = data["data"]["payload"]
                # Payload will be base64 RFC3548 encoded
                payload = base64.b64decode(payload)
                self._callback_execute('data', payload)
            else:
                _log.debug("Message not meant for me, ignoring")
        except Exception as e:
            _log.error("could not get payload data %s" % str(e))
            traceback.print_exc()

    def send(self, data):
        if self._proto:
            self._proto.sendCalvinMsg(self._token, data)
