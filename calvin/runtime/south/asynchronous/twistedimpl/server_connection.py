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
from calvin.common import certificate
from calvin.common import runtime_credentials
from twisted.internet import reactor, protocol, ssl, endpoints

from calvin.common.calvinlogger import get_logger
_log = get_logger(__name__)

from calvin.common import calvinconfig
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


# Local use only
class RawDataProtocol(Protocol):
    """A Calvin Server object"""
    def __init__(self, factory, max_length):
        self.MAX_LENGTH          = max_length
        self.data_available      = False
        self.connection_lost     = False
        self.factory             = factory
        self._data_buffer        = []

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


# Local use only
class LineProtocol(LineReceiver):
    def __init__(self, factory, delimiter):
        self.delimiter           = delimiter
        self.data_available      = False
        self.connection_lost     = False
        self._line_buffer        = []
        self.factory             = factory

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
            return data.decode('UTF-8') # TODO: Needs discussion
        else:
            raise Exception("Connection error: no data available")


# Local use only
class HTTPProtocol(LineReceiver):

    def __init__(self, factory):
        self.delimiter = b'\r\n\r\n'
        self.data_available = False
        self.connection_lost = False
        self._header = None
        self._data_buffer = b""
        self._data = None
        self.factory = factory
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
        line = line.decode('utf-8')
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
        if isinstance(data, str):
            data = data.encode('ascii')
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


# Local use only
# class ServerProtocolFactory(Factory):
#     def __init__(self, trigger, mode='line', delimiter=b'\r\n', max_length=8192, actor_id=None, node_name=None):
#
#         # TODO: Is this the way to do it:
#         if isinstance(delimiter, str):
#             self.delimiter = delimiter.encode('ascii')
#         else:
#             # assume bytes
#             self.delimiter = delimiter
#
#         self._trigger            = trigger
#         self.mode                = mode
#         self.MAX_LENGTH          = max_length
#         self.connections         = []
#         self.pending_connections = []
#         self._port               = None
#         self._actor_id           = actor_id
#         self._node_name          = node_name
#
#     def trigger(self):
#         self._trigger(self._actor_id)
#
#     def buildProtocol(self, addr):
#         if self.mode == 'line':
#             connection = LineProtocol(self, self.delimiter, actor_id=self._actor_id)
#         elif self.mode == 'raw':
#             connection = RawDataProtocol(self, self.MAX_LENGTH, actor_id=self._actor_id)
#         elif self.mode == 'http':
#             connection = HTTPProtocol(self, actor_id=self._actor_id)
#         else:
#             raise Exception("ServerProtocolFactory: Protocol not supported")
#         self.pending_connections.append((addr, connection))
#         return connection
#
#     def start(self, host, port):
#         self._port = reactor_listen(self._node_name, self, host, port)
#
#     def stop(self):
#         self._port.stopListening()
#         for c in self.connections:
#             c.transport.loseConnection()
#
#     def accept(self):
#         addr, conn = self.pending_connections.pop()
#         if not self.pending_connections:
#             self.connection_pending = False
#         return addr, conn

# ----------------------
# -     Public API     -
# ----------------------

class UDPServer(DatagramProtocol):
    def __init__(self, host, port, callback):
        self._callback = callback
        self.host = host
        self.port = port
        self._port = None
        self._data = []

    def datagramReceived(self, data, host_port_tuple):
        (host, port) = host_port_tuple
        message = {"host": host, "port": port, "data": data}
        self._data.append(message)
        self._callback()

    def have_data(self):
        return len(self._data) > 0

    def data_get(self):
        return self._data.pop(0)

    def start(self):
        try:
            self._port = reactor.listenUDP(self.port, self, interface=self.host)
        except Exception as exc:
            _log.exception(exc)
            _log.exception("Failed listening on port %s:%s", self.host, self.port)
            raise(exc)

    def stop(self):
        try:
            self._port.close()
        except Exception as exc:
            _log.info(exc)
            


class TCPServer(Factory):
    def __init__(self, callback, host, port, mode='line', node_name=None, **kwargs):

        # TODO: Is this the way to do it:
        delimiter = kwargs.get('delimiter', b'\r\n')
        if isinstance(delimiter, str):
            self.delimiter = delimiter.encode('ascii')
        else:
            # assume bytes
            self.delimiter = delimiter
            
        self._callback           = callback
        self.mode                = mode
        self.MAX_LENGTH          = kwargs.get('max_length', 8192)
        self.connections         = []
        self.pending_connections = []
        self.host                = host
        self.port                = port
        self._port               = None
        self._node_name          = node_name

    def trigger(self):
        self._callback()

    def buildProtocol(self, addr):
        if self.mode == 'line':
            connection = LineProtocol(self, self.delimiter)
        elif self.mode == 'raw':
            connection = RawDataProtocol(self, self.MAX_LENGTH)
        else:
            raise Exception("TCPServer: Protocol %s not supported" % self.mode)
        self.pending_connections.append((addr, connection))
        return connection

    def start(self):
        self._port = reactor_listen(self._node_name, self, self.host, self.port)

    def stop(self):
        self._port.stopListening()
        for c in self.connections:
            c.transport.loseConnection()

    def accept(self):
        addr, conn = self.pending_connections.pop()
        if not self.pending_connections:
            self.connection_pending = False
        return addr, conn


class HTTPServer(Factory):
    def __init__(self, callback, host, port, node_name=None):
        self._callback           = callback
        self.connections         = []
        self.pending_connections = []
        self.connection_map      = {}
        self.host                = host
        self.port                = port
        self._port               = None
        self._node_name          = node_name

    def trigger(self):
        """ Handle incoming requests on socket
        """
        print("trigger")
        if self.pending_connections:
            addr, conn = self.accept()
            self.connection_map[addr] = conn

        # N.B. Must use copy of connections.items here
        for handle, connection in list(self.connection_map.items()):
            if connection.data_available:
                command, headers, data = connection.data_get()
                print(handle, connection, command, headers, data)
                self._callback(handle, connection, command, headers, data)
    

    def buildProtocol(self, addr):
        connection = HTTPProtocol(self)
        self.pending_connections.append((addr, connection))
        return connection

    def start(self):
        self._port = reactor_listen(self._node_name, self, self.host, self.port)

    def stop(self):
        self._port.stopListening()
        for c in self.connections:
            c.transport.loseConnection()

    def accept(self):
        addr, conn = self.pending_connections.pop()
        if not self.pending_connections:
            self.connection_pending = False
        return addr, conn
        
    def send_response(self, handle, header, data):
        connection = self.connection_map[handle]
        if not connection.connection_lost:
            connection.send(header)
            if data:
                connection.send(data)
            connection.close()
        del self.connection_map[handle]
    
        
        
        
        
         