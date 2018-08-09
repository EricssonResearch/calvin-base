# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory
from twisted.internet.protocol import DatagramProtocol
from twisted.protocols.basic import LineReceiver
from twisted.internet import error
from calvin.utilities import certificate
from calvin.utilities import runtime_credentials
from twisted.internet import reactor, protocol, ssl, endpoints

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)

from calvin.utilities import calvinconfig
_conf = calvinconfig.get()


def reactor_listen(node_name, factory, host, port):
    listener = None

    control_interface_security = _conf.get("security", "control_interface_security")
    if control_interface_security == "tls":
        _log.debug("ServerProtocolFactory with TLS enabled chosen")
        try:
            # TODO: figure out how to set more than one root cert in twisted truststore
            runtime_cred = runtime_credentials.RuntimeCredentials(node_name)
            server_credentials_data = runtime_cred.get_credentials()
            server_credentials = ssl.PrivateCertificate.loadPEM(server_credentials_data)
        except Exception as err:
            _log.error("Failed to fetch server credentials, err={}".format(err))
            raise
        try:
            listener = reactor.listenSSL(port, factory, server_credentials.options(), interface=host)
        except Exception as err:
            _log.error("Server failed listenSSL, err={}".format(err))
    else:
        listener = reactor.listenTCP(port, factory, interface=host)
        # WORKAROUND This is here due to an obscure error in twisted trying to write to a listening port
        # on some architectures/OSes. The default is to raise a RuntimeError.
        listener.doWrite = lambda: None

    return listener


class UDPServerProtocol(DatagramProtocol):
    def __init__(self, trigger, actor_id):
        self._trigger = trigger
        self._actor_id = actor_id
        self._port = None
        self._data = []

    def datagramReceived(self, data, (host, port)):
        message = {"host": host, "port": port, "data": data}
        self._data.append(message)
        self._trigger(self._actor_id)

    def have_data(self):
        return len(self._data) > 0

    def data_get(self):
        if len(self._data) > 0:
            return self._data.pop(0)
        else:
            raise Exception("No data available")

    def start(self, interface, port):
        try:
            self._port = reactor.listenUDP(port, self, interface=interface)
        except error.CannotListenError:
            _log.exception("Could not listen on port %s:%s", interface, port)
            raise
        except Exception as exc:
            _log.exception("Failed when trying listening on port %s:%s", interface, port)
            raise


    def stop(self):
        self._port.close()


class RawDataProtocol(Protocol):
    """A Calvin Server object"""
    def __init__(self, factory, max_length, actor_id):
        self.MAX_LENGTH          = max_length
        self.data_available      = False
        self.connection_lost     = False
        self.factory             = factory
        self._data_buffer        = []
        self._actor_id = actor_id

    def connectionMade(self):
        self.factory.connections.append(self)
        self.factory.trigger()

    def connectionLost(self, reason):
        self.connection_lost = True
        self.factory.connections.remove(self)
        self.factory.trigger()

    def dataReceived(self, data):
        self.data_available = True
        while len(data) > 0:
            self._data_buffer.append(data[:self.MAX_LENGTH])
            data = data[self.MAX_LENGTH:]
        self.factory.trigger()

    def send(self, data):
        self.transport.write(data)

    def close(self):
        self.transport.loseConnection()

    def data_get(self):
        if self._data_buffer:
            data = self._data_buffer.pop(0)
            if not self._data_buffer:
                self.data_available = False
            return data
        else:
            raise Exception("Connection error: no data available")


class LineProtocol(LineReceiver):
    def __init__(self, factory, delimiter, actor_id):
        self.delimiter           = delimiter
        self.data_available      = False
        self.connection_lost     = False
        self._line_buffer             = []
        self.factory             = factory
        self._actor_id = actor_id

    def connectionMade(self):
        self.factory.connections.append(self)
        self.factory.trigger()

    def connectionLost(self, reason):
        self.connection_lost = True
        self.factory.connections.remove(self)
        self.factory.trigger()

    def lineReceived(self, line):
        self.data_available = True
        self._line_buffer.append(line)
        self.factory.trigger()

    def send(self, data):
        LineReceiver.sendLine(self, data)  # LineReceiver is an old style class.

    def close(self):
        self.transport.loseConnection()

    def data_get(self):
        self.line_length_exeeded = False
        if self._line_buffer:
            data = self._line_buffer.pop(0)
            if not self._line_buffer:
                self.data_available = False
            return data
        else:
            raise Exception("Connection error: no data available")


class HTTPProtocol(LineReceiver):

    def __init__(self, factory, actor_id):
        self.delimiter = '\r\n\r\n'
        self.data_available = False
        self.connection_lost = False
        self._header = None
        self._data_buffer = b""
        self._data = None
        self.factory = factory
        self._actor_id = actor_id
        self._expected_length = 0

        self.factory.connections.append(self)
        self.factory.trigger()

    def connectionLost(self, reason):
        self.connection_lost = True
        self.factory.connections.remove(self)
        self.factory.trigger()

    def rawDataReceived(self, data):
        self._data_buffer += data

        if self._expected_length - len(self._data_buffer) == 0:
            self._data = self._data_buffer
            self._data_buffer = b""
            self.data_available = True
            self.factory.trigger()

    def lineReceived(self, line):
        header = [h.strip() for h in line.split("\r\n")]
        self._command = header.pop(0)
        self._header = {}
        for attr in header:
            a, v = attr.split(':', 1)
            self._header[a.strip().lower()] = v.strip()
        self._expected_length = int(self._header.get('content-length', 0))
        if self._expected_length != 0:
            self.setRawMode()
        else:
            self.data_available = True
            self.factory.trigger()

    def send(self, data):
        # Do not add newlines - data may be binary
        self.transport.write(data)

    def close(self):
        self.transport.loseConnection()

    def data_get(self):
        if self.data_available:
            command = self._command
            headers = self._header
            if command.lower().startswith("get "):
                data = b""
            else:
                data = self._data
            self._header = None
            self._data = None
            self.data_available = False
            self.setLineMode()
            self._expected_length = 0
            return command, headers, data
        raise Exception("Connection error: no data available")


class ServerProtocolFactory(Factory):
    def __init__(self, trigger, mode='line', delimiter='\r\n', max_length=8192, actor_id=None, node_name=None):
        self._trigger            = trigger
        self.mode                = mode
        self.delimiter           = delimiter
        self.MAX_LENGTH          = max_length
        self.connections         = []
        self.pending_connections = []
        self._port               = None
        self._actor_id           = actor_id
        self._node_name          = node_name

    def trigger(self):
        self._trigger(self._actor_id)

    def buildProtocol(self, addr):
        if self.mode == 'line':
            connection = LineProtocol(self, self.delimiter, actor_id=self._actor_id)
        elif self.mode == 'raw':
            connection = RawDataProtocol(self, self.MAX_LENGTH, actor_id=self._actor_id)
        elif self.mode == 'http':
            connection = HTTPProtocol(self, actor_id=self._actor_id)
        else:
            raise Exception("ServerProtocolFactory: Protocol not supported")
        self.pending_connections.append((addr, connection))
        return connection

    def start(self, host, port):
        self._port = reactor_listen(self._node_name, self, host, port)

    def stop(self):
        self._port.stopListening()
        for c in self.connections:
            c.transport.loseConnection()

    def accept(self):
        addr, conn = self.pending_connections.pop()
        if not self.pending_connections:
            self.connection_pending = False
        return addr, conn
