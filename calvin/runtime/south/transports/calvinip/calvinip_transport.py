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

from calvin.utilities import calvinlogger
from twisted.twisted_transport import TwistedCalvinServer, TwistedCalvinTransport
from calvin.runtime.south.transports import base_transport
from calvin.runtime.south.transports.lib.twisted import twisted_transport

_log = calvinlogger.get_logger(__name__)


class CalvinTransportFactory(base_transport.BaseTransportFactory):
    def __init__(self, rt_id, node_name, callbacks):
        super(CalvinTransportFactory, self).__init__(rt_id, callbacks=callbacks)
        self._node_name = node_name
        self._peers = {}
        self._servers = {}
        self._callbacks = callbacks
        self._client_validator = None

    def join(self, uri, server_node_name=None):
        """docstring for join"""
        schema, peer_addr = uri.split(':', 1)
        if schema != 'calvinip':
            raise Exception("Cant handle schema %s!!" % schema)
        _log.debug("calvinip join %s", uri)
        try:
            tp = twisted_transport.CalvinTransport(self._rt_id,
                                                    uri, self._callbacks,
                                                    TwistedCalvinTransport,
                                                    node_name=self._node_name,
                                                    client_validator=self._client_validator,
                                                    server_node_name=server_node_name)
            self._peers[peer_addr] = tp
            tp.connect()
            return tp
        except:
            _log.exception("Error creating TwistedCalvinTransport")
            raise

    def _get_uri(self, uri):
        if uri == "calvinip://default":
            # Need to form a proper default uri
            uri = "calvinip://0.0.0.0"
        return uri

    def listen(self, uri):
        _log.debug("Listen incoming uri %s", uri)
        uri = self._get_uri(uri)
        schema, _peer_addr = uri.split(':', 1)
        if schema != 'calvinip':
            raise Exception("Cant handle schema %s!!" % schema)

        if uri in self._servers:
            raise Exception("Server already started!!" % uri)

        try:
            tp = twisted_transport.CalvinServer(
                self._rt_id, self._node_name, uri, self._callbacks, TwistedCalvinServer, TwistedCalvinTransport,
                client_validator=self._client_validator)
            port = tp.start()
            _log.debug("Listen real uri %s", uri)
            self._servers[uri] = tp
            return tp
        except:
            _log.exception("Error starting server")
            raise

    def stop_listening(self, uri):
        _log.debug("Stop listnening %s", uri)
        uri = self._get_uri(uri)
        if uri in self._servers:
            server = self._servers.pop(uri)
            server.stop()
