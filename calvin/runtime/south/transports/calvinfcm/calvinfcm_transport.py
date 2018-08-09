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
from calvin.runtime.south.transports import base_transport
from twisted.twisted_transport import TwistedCalvinTransport, TwistedCalvinTransportClient
from calvin.runtime.south.transports.lib.twisted import twisted_transport

_log = calvinlogger.get_logger(__name__)

class CalvinTransportFactory(base_transport.BaseTransportFactory):

    def __init__(self, rt_id, node_name, callbacks):
        super(CalvinTransportFactory, self).__init__(rt_id, callbacks=callbacks)
        self._callbacks = callbacks
        self._node_name = node_name
        self._peers = {}
        self._servers = {}

    def join(self, uri):
        _log.debug("Was sent join request to calvin")
        #TODO: Return same tp as we created in listen?
        schema, peer_addr = uri.split(':', 1)
        if schema != 'calvinfcm':
            raise Exception("Cant handle schema %s!!" % schema)
        try:
            uri = URI(uri)
            server = self._servers.get("calvinfcm://%s:*" % uri.hostname)
            if server is not None:
                try:
                    proto = server.protocol_factory.proto
                except Exception as e:
                    _log.error("No protocol factory found when joining.")
                    return None
                return server._callback_execute('client_connected', create_uri(self.hostname, uri.port), proto)
            else:
                raise Exception("Server not started, start server to connect to FCM")
        except:
            _log.exception("Error creating TwistedCalvinTransport")
            raise

    def listen(self, uri):
        schema, peer_addr = uri.split(":", 1)
        if schema != "calvinfcm":
            raise Exception("Unable to handle schema %s" % schema)
        try:
            tp = twisted_transport.CalvinServer(
                                    self._rt_id,
                                    self._node_name,
                                    uri,
                                    self._callbacks,
                                    TwistedCalvinTransport,
                                    TwistedCalvinTransportClient,
                                    client_validator=None)
            self._servers[uri] = tp
            tp.start()
            return tp
        except:
            _log.exception("Error starting server")
            raise
