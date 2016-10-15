# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.actor.actorport import PortMeta
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.port.connection.common import BaseConnection, PURPOSE
from calvin.runtime.north.plugins.port import DISCONNECT

_log = calvinlogger.get_logger(__name__)


# Connection methods
_MODULES = {'local': 'LocalConnection',
            'tunnel': 'TunnelConnection'}
from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


for module, class_ in _MODULES.items():
    module_obj = __import__(module, globals=globals())
    globals()[class_] = getattr(module_obj, class_)


class ConnectionFactory(object):
    """ Set up a connection between ports according to port properties
        node: the node
        purpose: INIT, CONNECT or DISCONNECT
    """

    def __init__(self, node, purpose, **kwargs):
        super(ConnectionFactory, self).__init__()
        self.kwargs = kwargs
        self.node = node
        self.purpose = purpose

    def get(self, port, peer_port_meta, callback=None, **kwargs):
        if peer_port_meta.is_local():
            return LocalConnection(self.node, self.purpose, port, peer_port_meta, callback, self, **kwargs)
        elif self.purpose == PURPOSE.DISCONNECT and peer_port_meta.node_id is None:
            # A port that miss node info that we want to disconnect is already disconnected
            return Disconnected(self.node, self.purpose, port, peer_port_meta, callback, self, **kwargs)
        else:
            # Remote connection
            # TODO Currently we only have support for setting up a remote connection via tunnel
            return TunnelConnection(self.node, self.purpose, port, peer_port_meta, callback, self, **kwargs)

    def get_existing(self, port_id, callback=None, **kwargs):
        _log.analyze(self.node.id, "+", {'port_id': port_id})
        port_meta = PortMeta(self.node.pm, port_id=port_id)
        if not port_meta.is_local():
            status = response.CalvinResponse(response.NOT_FOUND, "Port %s must be local" % (port_id))
            if callback:
                callback(status=status, port_id=port_id)
                return
            else:
                raise response.CalvinResponseException(status)
        _log.analyze(self.node.id, "+ LOCAL CHECKED", {'port_id': port_id})
        port = port_meta.port
        # Now check the peer port, peer_ids is list of (peer_node_id, peer_port_id) tuples
        peer_ids = port.get_peers()

        _log.analyze(self.node.id, "+ GOT PEERS", {'port_id': port_id, 'peer_ids': peer_ids})
        # A port may have several peers, create individual connection instances
        connections = []
        for peer_id in peer_ids:
            # When node id is 'local' it is local
            peer_node_id = self.node.id if peer_id[0] == 'local' else peer_id[0]
            peer_port_meta = PortMeta(
                                self.node.pm,
                                port_id=peer_id[1], node_id=peer_node_id)
            connections.append(self.get(port, peer_port_meta, callback, **kwargs))
        # Make a connection instance aware of all parallel connection instances
        for connection in connections:
            connection.parallel_connections(connections)
        _log.analyze(self.node.id, "+ DONE", {'port_id': port_id})
        return connections

    def init(self):
        data = {}
        for class_name in _MODULES.values():
            _log.debug("Init connection method %s" % class_name)
            C = globals()[class_name]
            data[C.__name__] = C(self.node, PURPOSE.INIT, None, None, None, self, **self.kwargs).init()
        return data

class Disconnected(BaseConnection):
    """ When a peer already is disconnected """

    def __init__(self, node, purpose, port, peer_port_meta, callback, factory, **kwargs):
        super(Disconnected, self).__init__(node, purpose, port, peer_port_meta, callback, factory)
        self.kwargs = kwargs

    def disconnect(self, terminate=DISCONNECT.TEMPORARY):
        if self.callback:
            self.callback(status=response.CalvinResponse(True), port_id=self.port.id)
