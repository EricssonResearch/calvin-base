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
from calvin.runtime.south.plugins.transports import base_transport
from calvin.runtime.south.plugins.transports.lib.twisted import twisted_transport

_log = calvinlogger.get_logger(__name__)


class CalvinTransportFactory(base_transport.BaseTransportFactory):

    def __init__(self, rt_id, callbacks):
        super(CalvinTransportFactory, self).__init__(rt_id, callbacks=callbacks)
        self._peers = {}
        self._servers = {}
        self._callbacks = callbacks

    def _peer_connected(self):
        pass

    def join(self, uri):
        """docstring for join"""
        schema, peer_addr = uri.split(':', 1)
        if schema != 'calvinbt':
            raise Exception("Cant handle schema %s!!" % schema)

        try:
            tp = twisted_transport.CalvinTransport(self._rt_id, uri, self._callbacks,
                                                   TwistedCalvinTransport)
            self._peers[peer_addr] = tp
            tp.connect()
            # self._callback_execute('join_finished', peer_id, tp)
            return True
        except:
            _log.exception("Error creating TwistedCalvinTransport")
            raise

    def listen(self, uri):
        schema, port = uri.split(':', 1)
        if schema != 'calvinbt':
            raise Exception("Cant handle schema %s!!" % schema)

        if uri in self._servers:
            raise Exception("Server already started!!" % uri)

        try:
            tp = twisted_transport.CalvinServer(
                self._rt_id, uri, self._callbacks, TwistedCalvinServer, TwistedCalvinTransport)
            self._servers[uri] = tp
            tp.start()
        except:
            _log.exception("Error starting server")
            raise
