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
from calvin.utilities import certificate
from calvin.utilities import runtime_credentials
from calvin.runtime.south.transports.lib.twisted import base_transport

from twisted.protocols.basic import Int32StringReceiver
from twisted.internet import error
from twisted.internet import reactor, protocol, ssl, endpoints

_log = calvinlogger.get_logger(__name__)

from calvin.utilities import calvinconfig
_conf = calvinconfig.get()


def create_uri(ip, port):
    return "%s://%s:%s" % ("calvinip", ip, port)


# Server
class TwistedCalvinServer(base_transport.CalvinServerBase):
    """
    """

    def __init__(self, iface='', node_name=None, port=0, callbacks=None, *args, **kwargs):
        super(TwistedCalvinServer, self).__init__(callbacks=callbacks)
        self._iface = iface
        self._node_name=node_name
        self._port = port
        self._addr = None
        self._tcp_server = None
        self._callbacks = callbacks
        self._runtime_credentials = None

    def start(self):
        callbacks = {'connected': [CalvinCB(self._connected)]}
        tcp_f = TCPServerFactory(callbacks)
        runtime_to_runtime_security = _conf.get("security","runtime_to_runtime_security")
        trusted_ca_certs = []
        if runtime_to_runtime_security=="tls":
            _log.debug("TwistedCalvinServer with TLS chosen")
            try:
                self._runtime_credentials = runtime_credentials.RuntimeCredentials(self._node_name)
                ca_cert_list_str =certificate.get_truststore_as_list_of_strings(certificate.TRUSTSTORE_TRANSPORT)
                for ca_cert in ca_cert_list_str:
                    trusted_ca_certs.append(ssl.Certificate.loadPEM(ca_cert))
                server_credentials_data = self._runtime_credentials.get_credentials()
                server_credentials = ssl.PrivateCertificate.loadPEM(server_credentials_data)
            except Exception as err:
                _log.exception("Server failed to load credentials, err={}".format(err))
            try:
                self._tcp_server = reactor.listenSSL(self._port, tcp_f, server_credentials.options(*trusted_ca_certs), interface=self._iface)
            except Exception as err:
                _log.exception("Server failed listenSSL, err={}".format(err))
        else:
            _log.debug("TwistedCalvinServer without TLS chosen")
            try:
                self._tcp_server = reactor.listenTCP(self._port, tcp_f, interface=self._iface)
            except error.CannotListenError:
                _log.exception("Could not listen on port %s:%s", self._iface, self._port)
                raise
            except Exception as exc:
                _log.exception("Failed when trying listening on port %s:%s", self._iface, self._port)
                raise
        self._port = self._tcp_server.getHost().port
        self._callback_execute('server_started', self._port)
        return self._port

    def stop(self):
        _log.debug("Stopping server %s", self._tcp_server)
        def fire_callback(args):
            _log.debug("Server stopped %s", self._tcp_server)
            self._callback_execute('server_stopped')
        def fire_errback(args):
            _log.warning("Server did not stop as excpected %s", args)
            self._callback_execute('server_stopped')

        if self._tcp_server:
            d = self._tcp_server.stopListening()
            self._tcp_server = None
            d.addCallback(fire_callback)
            d.addErrback(fire_errback)

    def is_listening(self):
        return self._tcp_server is not None

    def _connected(self, proto):
        self._callback_execute('client_connected', create_uri(proto.transport.getPeer().host,
                                                              proto.transport.getPeer().port), proto)


class StringProtocol(CalvinCBClass, Int32StringReceiver):
    def __init__(self, callbacks):
        super(StringProtocol, self).__init__(callbacks)
        self._callback_execute('set_proto', self)
        self.MAX_LENGTH = 1024*1024*20

    def connectionMade(self):
        self._callback_execute('connected', self)

    def lengthLimitExceeded(self, length):
        _log.error("String length recieved to big package was dumped, length was %s and max length is %s", length, self.MAX_LENGTH)

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
    def __init__(self, host, port, callbacks=None, proto=None, node_name=None, server_node_name=None, *args, **kwargs):
        super(TwistedCalvinTransport, self).__init__(host, port, callbacks=callbacks)
        self._host_ip = host
        self._host_port = port
        self._proto = proto
        self._factory = None
        self._node_name = node_name
        self._server_node_name=server_node_name
        self._runtime_credentials = None

        # Server created us already have a proto
        if proto:
            proto.callback_register('connected', CalvinCB(self._connected))
            proto.callback_register('disconnected', CalvinCB(self._disconnected))
            proto.callback_register('data', CalvinCB(self._data))

        self._callbacks = callbacks

        #If TLS is chosen, ensure that a node_name and a server_node_name are set
        runtime_to_runtime_security = _conf.get("security","runtime_to_runtime_security")
        if (runtime_to_runtime_security=="tls"):
            if self._node_name==None or self._server_node_name==None:
                _log.error("For TLS, both node_name and server_node_name must be given as input"
                                "\n\tself._node_name={}"
                                "\n\tself._server_node_name={}".format(self._node_name, self._server_node_name))
                raise Exception("For TLS, both node_name and server_node_name must be given as input")

    def is_connected(self):
        return self._proto is not None

    def disconnect(self):
        if self._proto:
            self._proto.transport.loseConnection()

    def send(self, data):
        if self._proto:
            self._proto.sendString(data)

    def join(self):
        from twisted.internet._sslverify import OpenSSLCertificateAuthorities
        from OpenSSL import crypto
        if self._proto:
            raise Exception("Already connected")

        # Own callbacks
        callbacks = {'connected': [CalvinCB(self._connected)],
                     'disconnected': [CalvinCB(self._disconnected)],
                     'connection_failed': [CalvinCB(self._connection_failed)],
                     'data': [CalvinCB(self._data)],
                     'set_proto': [CalvinCB(self._set_proto)]}

        self._factory = TCPClientFactory(callbacks) # addr="%s:%s" % (self._host_ip, self._host_port))
        runtime_to_runtime_security = _conf.get("security","runtime_to_runtime_security")
        if runtime_to_runtime_security=="tls":
            _log.debug("TwistedCalvinTransport with TLS chosen")
            trusted_ca_certs = []
            try:
                self._runtime_credentials = runtime_credentials.RuntimeCredentials(self._node_name)
                ca_cert_list_str = certificate.get_truststore_as_list_of_strings(certificate.TRUSTSTORE_TRANSPORT)
                for ca_cert in ca_cert_list_str:
                    trusted_ca_certs.append(crypto.load_certificate(crypto.FILETYPE_PEM, ca_cert))
                ca_certs = OpenSSLCertificateAuthorities(trusted_ca_certs)
                client_credentials_data =self._runtime_credentials.get_credentials()
                client_credentials = ssl.PrivateCertificate.loadPEM(client_credentials_data)
            except Exception as err:
                _log.error("TwistedCalvinTransport: Failed to load client credentials, err={}".format(err))
                raise
            try:
                options = ssl.optionsForClientTLS(self._server_node_name,
                                                   trustRoot=ca_certs,
                                                   clientCertificate=client_credentials)
            except Exception as err:
                _log.error("TwistedCalvinTransport: Failed to create optionsForClientTLS "
                                "\n\terr={}"
                                "\n\tself._server_node_name={}".format(err,
                                                                      self._server_node_name))
                raise
            try:
                endpoint = endpoints.SSL4ClientEndpoint(reactor,
                                                        self._host_ip,
                                                        int(self._host_port),
                                                        options)
            except:
                _log.error("TwistedCalvinTransport: Client failed connectSSL")
                raise
            try:
                endpoint.connect(self._factory)
            except Exception as e:
                _log.error("TwistedCalvinTransport: Failed endpoint.connect, e={}".format(e))
                raise
        else:
            reactor.connectTCP(self._host_ip, int(self._host_port), self._factory)

    def _set_proto(self, proto):
        _log.debug("%s, %s, %s" % (self, '_set_proto', proto))
        if self._proto:
            _log.error("_set_proto: Already connected")
            return
        self._proto = proto

    def _connected(self, proto):
        _log.debug("%s, %s" % (self, 'connected'))
        self._callback_execute('connected')

    def _disconnected(self, reason):
        _log.debug("%s, %s, %s" % (self, 'disconnected', reason))
        self._callback_execute('disconnected', reason)

    def _connection_failed(self, addr, reason):
        _log.debug("%s, %s, %s" % (self, 'connection_failed', reason))
        self._callback_execute('connection_failed', reason)

    def _data(self, data):
        _log.debug("%s, %s, %s" % (self, '_data', data))
        self._callback_execute('data', data)


class TCPClientFactory(protocol.ClientFactory, CalvinCBClass):
    protocol = StringProtocol

    def __init__(self, callbacks):
        # For the protocol
        self._callbacks = callbacks
        super(TCPClientFactory, self).__init__(callbacks)

    def clientConnectionFailed(self, connector, reason):
        _log.info('Connection failed. reason: %s, dest %s', reason, connector.getDestination())
        addr = (connector.getDestination().host, connector.getDestination().port)
        self._callback_execute('connection_failed', addr, reason)

    def startedConnecting(self, connector):
        pass

    def buildProtocol(self, addr):
        proto = self.protocol(self._callbacks)
        return proto
