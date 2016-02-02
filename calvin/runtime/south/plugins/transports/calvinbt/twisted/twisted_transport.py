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

from calvin.utilities.calvin_callback import CalvinCB, CalvinCBClass
from calvin.utilities import calvinlogger
from calvin.runtime.south.plugins.transports.lib.twisted import base_transport
from calvin.runtime.south.plugins.transports.calvinbt.twisted import bt

from twisted.protocols.basic import Int32StringReceiver
from twisted.internet import protocol, reactor

_log = calvinlogger.get_logger(__name__)


def create_uri(id, port):
    return "%s://%s:%s" % ("calvinbt", id, port)


# Server
class TwistedCalvinServer(base_transport.CalvinServerBase):

    """
    """

    def __init__(self, iface='', port=0, callbacks=None, *args, **kwargs):
        super(TwistedCalvinServer, self).__init__(callbacks=callbacks)
        self._iface = iface
        self._port = port
        self._addr = None
        self._tcp_server = None
        self._callbacks = callbacks

    def start(self):
        callbacks = {'connected': [CalvinCB(self._connected)]}
        tcp_f = TCPServerFactory(callbacks)

        self._tcp_server = bt.BtPort(port=int(self._port), factory=tcp_f, interface=self._iface)
        self._tcp_server.startListening()
        self._port = self._tcp_server.getHost()[1]
        self._callback_execute('server_started', self._port)
        return self._port

    def stop(self):
        def fire_callback(args):
            self._callback_execute('server_stopped')
        if self._tcp_server:
            d = self._tcp_server.stopListening()
            self._tcp_server = None
            d.addCallback(fire_callback)

    def is_listening(self):
        return self._tcp_server is not None

    def _connected(self, proto):
        self._callback_execute('client_connected', create_uri(proto.transport.getPeer()[0],
                                                              proto.transport.getPeer()[1]), proto)


class StringProtocol(CalvinCBClass, Int32StringReceiver):

    def __init__(self, callbacks):
        super(StringProtocol, self).__init__(callbacks)
        self._callback_execute('set_proto', self)

    def connectionMade(self):
        self._callback_execute('connected', self)

    def connectionLost(self, reason):
        self._callback_execute('disconnected', reason)
        # TODO: Remove all callbacks

    def stringReceived(self, data):
        "As soon as any data is received, send it to callback"
        self._callback_execute('data', data)


class TCPServerFactory(protocol.ServerFactory):
    protocol = StringProtocol

    def __init__(self, callbacks):
        # For the protocol
        self._callbacks = callbacks

    def buildProtocol(self, addr):
        proto = self.protocol(self._callbacks)
        return proto


# Client
class TwistedCalvinTransport(base_transport.CalvinTransportBase):

    def __init__(self, host, port, callbacks=None, proto=None, *args, **kwargs):
        super(TwistedCalvinTransport, self).__init__(host, port, callbacks=callbacks)
        self._host_ip = host
        self._host_port = port
        self._proto = proto
        self._factory = None

        # Server created us already have a proto
        if proto:
            proto.callback_register('connected', CalvinCB(self._connected))
            proto.callback_register('disconnected', CalvinCB(self._disconnected))
            proto.callback_register('data', CalvinCB(self._data))

        self._callbacks = callbacks

    def is_connected(self):
        return self._proto is not None

    def disconnect(self):
        if self._proto:
            self._proto.transport.loseConnection()

    def send(self, data):
        if self._proto:
            self._proto.sendString(data)

    def join(self):  # , callbacks):
        if self._proto:
            raise Exception("Already connected")

        # Own callbacks
        callbacks = {'connected': [CalvinCB(self._connected)],
                     'disconnected': [CalvinCB(self._disconnected)],
                     'data': [CalvinCB(self._data)],
                     'set_proto': [CalvinCB(self._set_proto)]}

        self._factory = TCPClientFactory(callbacks)
        c = bt.BtConnector(host=self._host_ip, port=int(self._host_port),
                           factory=self._factory, timeout=30, bindAddress=None, reactor=reactor)
        c.connect()

    def _set_proto(self, proto):
        _log.debug("%s, %s, %s" % (self, '_set_proto', proto))
        self._proto = proto

    def _connected(self, proto):
        _log.debug("%s, %s" % (self, 'connected'))
        self._callback_execute('connected')

    def _disconnected(self, reason):
        _log.debug("%s, %s, %s" % (self, 'disconnected', reason))
        self._callback_execute('disconnected', str(reason))

    def _data(self, data):
        _log.debug("%s, %s, %s" % (self, '_data', data))
        self._callback_execute('data', data)


class TCPClientFactory(protocol.ClientFactory):
    protocol = StringProtocol

    def __init__(self, callbacks):
        # For the protocol
        self._callbacks = callbacks

    def startedConnecting(self, connector):
        pass

    def buildProtocol(self, addr):
        proto = self.protocol(self._callbacks)
        return proto
