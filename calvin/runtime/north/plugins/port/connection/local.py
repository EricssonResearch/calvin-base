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

from calvin.runtime.north.plugins.port import endpoint
from calvin.runtime.north.plugins.port import queue
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.port.connection.common import BaseConnection
from calvin.runtime.north.plugins.port import DISCONNECT

_log = calvinlogger.get_logger(__name__)


class LocalConnection(BaseConnection):
    """ Connect two ports that are local"""

    def __init__(self, node, purpose, port, peer_port_meta, callback, factory, **kwargs):
        super(LocalConnection, self).__init__(node, purpose, port, peer_port_meta, callback, factory)
        self.kwargs = kwargs

    def connect(self):
        _log.analyze(self.node.id, "+ LOCAL", {'local_port': self.port, 'peer_port': self.peer_port_meta},
                        peer_node_id=self.peer_port_meta.node_id)
        port1 = self.port
        try:
            port2 = self.peer_port_meta.port
        except:
            # Should have been local but have moved
            # Need ConnectionFactory to redo its job.
            _log.analyze(self.node.id, "+ LOCAL-TO-TUNNELED", {'factory': self.factory})
            def _factory_connect(status, port_meta):
                # TODO check retry to not get into infinte loop?
                if not status:
                    self.async_reply(status=status.status)
                self.factory.get(self.port, self.peer_port_meta, self.callback).connect()
            self.peer_port_meta.retry(_factory_connect)
            return

        # Local connect wants the first port to be an inport
        inport, outport = (port1, port2) if port1.direction == 'in' else (port2, port1)
        self._connect_via_local(inport, outport)
        self.async_reply(status=response.CalvinResponse(True))
        return None

    def _connect_via_local(self, inport, outport):
        """ Both connecting ports are local, just connect them """
        _log.analyze(self.node.id, "+", {})
        inport.set_queue(queue.get(inport, peer_port=outport))
        outport.set_queue(queue.get(outport, peer_port=inport))
        ein = endpoint.LocalInEndpoint(inport, outport, self.node.sched)
        eout = endpoint.LocalOutEndpoint(outport, inport, self.node.sched)

        invalid_endpoint = outport.attach_endpoint(eout)
        invalid_endpoint.unregister(self.node.sched)
        invalid_endpoint.destroy()
        eout.register(self.node.sched)
        invalid_endpoint = inport.attach_endpoint(ein)
        invalid_endpoint.unregister(self.node.sched)
        invalid_endpoint.destroy()
        ein.register(self.node.sched)

        # Update storage
        self.node.storage.add_port(inport, self.node.id, inport.owner.id)
        self.node.storage.add_port(outport, self.node.id, outport.owner.id)

    def disconnect(self, terminate=DISCONNECT.TEMPORARY):
        """ Obtain any missing information to enable disconnecting one peer port and make the disconnect"""

        _log.analyze(self.node.id, "+", {'port_id': self.port.id})
        endpoints = self.port.disconnect(peer_ids=[self.peer_port_meta.port_id], terminate=terminate)
        _log.analyze(self.node.id, "+ EP", {'port_id': self.port.id, 'endpoints': endpoints})
        remaining_tokens = {}
        # Can only be one for the one peer as argument to disconnect, but loop for simplicity
        for ep in endpoints:
            remaining_tokens.update(ep.remaining_tokens)
            ep.unregister(self.node.sched)
            ep.destroy()
        _log.analyze(self.node.id, "+ EP DESTROYED", {'port_id': self.port.id})

        # Disconnect other end also, which is also local
        terminate_peer = DISCONNECT.EXHAUST_PEER if terminate == DISCONNECT.EXHAUST else terminate
        endpoints = self.peer_port_meta.port.disconnect(peer_ids=[self.port.id], terminate=terminate_peer)
        _log.analyze(self.node.id, "+ EP PEER", {'port_id': self.port.id, 'endpoints': endpoints})
        peer_remaining_tokens = {}
        # Can only be one for the one peer as argument to disconnect, but loop for simplicity
        for ep in endpoints:
            peer_remaining_tokens.update(ep.remaining_tokens)
            ep.unregister(self.node.sched)
            ep.destroy()
        _log.analyze(self.node.id, "+ DISCONNECTED", {'port_id': self.port.id})

        self.port.exhausted_tokens(peer_remaining_tokens)
        self.peer_port_meta.port.exhausted_tokens(remaining_tokens)

        # Update storage, the ports are disconnected even if an inport during exhaustion still delivers tokens
        if terminate:
            self.node.storage.add_port(self.port, self.node.id, self.port.owner.id,
                                        exhausting_peers=peer_remaining_tokens.keys())
            self.node.storage.add_port(self.peer_port_meta.port, self.node.id, self.peer_port_meta.port.owner.id,
                                        exhausting_peers=remaining_tokens.keys())

        try:
            # Remove this peer from the list of peer connections
            self._parallel_connections.remove(self)
        except:
            pass
        if not getattr(self, 'sent_callback', False) and not self._parallel_connections:
            _log.analyze(self.node.id, "+ SEND OK", {'port_id': self.port.id})
            # Last peer connection we should send OK
            if self.callback:
                self.callback(status=response.CalvinResponse(True), port_id=self.port.id)
