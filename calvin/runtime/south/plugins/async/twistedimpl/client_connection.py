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

from twisted.protocols import basic
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet.protocol import DatagramProtocol

from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCBClass

_log = get_logger(__name__)


class DummyError(object):
    def __init__(self, str_):
        self._str = str_

    def getErrorMessage(self):
        return self._str


class UDPRawProtocol(CalvinCBClass, DatagramProtocol):
    def __init__(self, callbacks=None, **kwargs):
        super(UDPRawProtocol, self).__init__(callbacks)
        self.host = kwargs.pop('host', '')
        self.port = kwargs.pop('port', 0)
        self.factory = kwargs.pop('factory', None)

    def startProtocol(self):
        self.transport.connect(self.host, self.port)

    def stopProtocol(self):
        "Called after all transport is teared down"
        self.factory.clientConnectionLost(None, DummyError("disconnected"))

    def datagramReceived(self, data, (host, port)):
        self._callback_execute('data_received', data)

    def send(self, data):
        self.transport.write(data, (self.host, self.port))


class RawProtocol(CalvinCBClass, Protocol):
    def __init__(self, callbacks=None, **kwargs):
        super(RawProtocol, self).__init__(callbacks)
        self.host = kwargs.pop('host', '')
        self.port = kwargs.pop('port', 0)

    def dataReceived(self, data):
        self._callback_execute('data_received', data)

    def send(self, data):
        self.transport.write(data)

    def close(self):
        self.transport.loseConnection()


class StringRecieverProtocol(CalvinCBClass, basic.Int16StringReceiver):
    def __init__(self, callbacks=None, **kwargs):
        super(StringRecieverProtocol, self).__init__(callbacks)
        self.host = kwargs.pop('host', '')
        self.port = kwargs.pop('port', 0)

    def stringReceived(self, data):
        self._callback_execute('data_received', data)


class DelimiterProtocol(CalvinCBClass, basic.LineReceiver):
    def __init__(self, callbacks=None, **kwargs):
        self.delimiter = kwargs.pop('delimiter', '\r\n')
        self.host = kwargs.pop('host', '')
        self.port = kwargs.pop('port', 0)
        super(DelimiterProtocol, self).__init__(callbacks)

    def lineReceived(self, data):
        self._callback_execute('data_received', data)


class BaseClientProtocolFactory(CalvinCBClass, ClientFactory):
    def __init__(self, callbacks=None):
        super(BaseClientProtocolFactory, self).__init__(callbacks)
        self._callbacks = callbacks
        self._addr = ""
        self._port = 0
        self._delimiter = None

    def startedConnecting(self, connector):
        pass

    def buildProtocol(self, addr):
        self.protocol = self._protocol_factory({'data_received': self._callbacks['data_received']},
                                               delimiter=self._delimiter, host=self._addr, port=self._port,
                                               factory=self)
        reactor.callLater(0, self._callback_execute, 'connected', addr)
        return self.protocol

    def disconnect(self):
        if self._connector:
            # TODO: returns defered ?!?
            self._connector.disconnect()
        self.protocol = None

    def send(self, data):
        self.protocol.send(data)

    def clientConnectionLost(self, connector, reason):
        self._callback_execute('connection_lost', connector, reason)
        self._callback_execute('connection_lost', (self._addr, self._port), reason.getErrorMessage())

    # TODO: returns defered ?!?
    def clientConnectionFailed(self, connector, reason):
        self._callback_execute('connection_failed', (self._addr, self._port), reason.getErrorMessage())


class UDPClientProtocolFactory(BaseClientProtocolFactory):
    def __init__(self, callbacks=None):
        super(UDPClientProtocolFactory, self).__init__(callbacks)
        self._addr = ""
        self._port = 0
        self._protocol_factory = UDPRawProtocol

    def connect(self, addr, port):
        self._addr = addr
        self._port = port
        self._connector = reactor.listenUDP(0, self.buildProtocol((addr, port)))
        return self._connector


class TCPClientProtocolFactory(BaseClientProtocolFactory):
    def __init__(self, mode, delimiter="\r\n", callbacks=None):
        super(TCPClientProtocolFactory, self).__init__(callbacks)
        self._protocol_factory = None
        self._protocol_type = mode
        self.protocol = None
        self._connector = None
        self._delimiter = delimiter
        self._addr = ""
        self._port = 0

        if mode == "raw":
            self._protocol_factory = RawProtocol
        elif mode == "string":
            self._protocol_factory = StringRecieverProtocol
        elif mode == "delimiter":
            self._protocol_factory = DelimiterProtocol
        else:
            _log.error("Trying use non existing protocol %s !" % (mode, ))
            raise Exception("Trying use non existing protocol %s !" % (mode, ))

    def connect(self, addr, port):
        self._addr = addr
        self._port = port

        return reactor.connectTCP(addr, port, self)

    def send(self, data):
        if self._protocol_type == "raw":
            self.protocol.send(data)
        elif self._protocol_type == "string":
            self.protocol.sendString(data)
        elif self._protocol_type == "delimiter":
            self.protocol.sendLine(data)
        else:
            _log.error("Trying use non existing protocol %s !" % self._protocol_type)
