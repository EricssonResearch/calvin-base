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

from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.north.plugins.port import endpoint
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.calvin_proto import CalvinTunnel
from calvin.runtime.north.plugins.port import queue
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.port.connection.common import BaseConnection, PURPOSE
from calvin.runtime.north.plugins.port import DISCONNECT

_log = calvinlogger.get_logger(__name__)


class TunnelConnection(BaseConnection):
    """ Connect two ports that are remote over a Tunnel"""

    def __init__(self, node, purpose, port, peer_port_meta, callback, factory, **kwargs):
        super(TunnelConnection, self).__init__(node, purpose, port, peer_port_meta, callback, factory)
        self.kwargs = kwargs
        if self.purpose != PURPOSE.INIT:
            self.token_tunnel = self.node.pm.connections_data[self.__class__.__name__]

    def connect(self, status=None, port_meta=None):
        # TODO: status & port_meta unused
        if self.peer_port_meta.node_id == self.node.id:
            # The peer port has moved to this node!
            if not self.peer_port_meta.check_still_local():
                # but gone before we reacted, chase it again
                # TODO check retry to not get into infinte loop?
                self.peer_port_meta.retry(callback=self.connect)
                return
            # Need ConnectionFactory to redo its job.
            _log.analyze(self.node.id, "+ TUNNELED-TO-LOCAL", {'factory': self.factory})
            self.factory.get(self.port, self.peer_port_meta, self.callback).connect()
            return
        tunnel = None
        self.peer_port_meta.retries = 0
        if self.peer_port_meta.node_id not in self.token_tunnel.tunnels.iterkeys():
            # No tunnel to peer, get one first
            _log.analyze(self.node.id, "+ GET TUNNEL", self.peer_port_meta, peer_node_id=self.peer_port_meta.node_id)
            tunnel = self.node.proto.tunnel_new(self.peer_port_meta.node_id, 'token', {})
            tunnel.register_tunnel_down(CalvinCB(self.token_tunnel.tunnel_down, tunnel))
            tunnel.register_tunnel_up(CalvinCB(self.token_tunnel.tunnel_up, tunnel))
            tunnel.register_recv(CalvinCB(self.token_tunnel.tunnel_recv_handler, tunnel))
            self.token_tunnel.tunnels[self.peer_port_meta.node_id] = tunnel
        else:
            tunnel = self.token_tunnel.tunnels[self.peer_port_meta.node_id]

        if tunnel.status == CalvinTunnel.STATUS.PENDING:
            if self.peer_port_meta.node_id not in self.token_tunnel.pending_tunnels:
                self.token_tunnel.pending_tunnels[self.peer_port_meta.node_id] = []
            # call _connect_via_tunnel when we get the response of the tunnel
            self.token_tunnel.pending_tunnels[self.peer_port_meta.node_id].append(CalvinCB(self._connect_via_tunnel))
            return
        if tunnel.status == CalvinTunnel.STATUS.TERMINATED:
            # TODO should we retry at this level?
            self.async_reply(status=response.CalvinResponse(response.INTERNAL_ERROR))
            return

        _log.analyze(self.node.id, "+ HAD TUNNEL",
                        {'local_port': self.port, 'peer_port': self.peer_port_meta,
                        'tunnel_status': self.token_tunnel.tunnels[self.peer_port_meta.node_id].status},
                        peer_node_id=self.peer_port_meta.node_id)
        self._connect_via_tunnel(status=response.CalvinResponse(True))

    def _connect_via_tunnel(self, status=None):
        """ All information and hopefully (status OK) a tunnel to the peer is available for a port connect"""
        _log.analyze(self.node.id, "+ " + str(status),
                     {'local_port': self.port, 'peer_port': self.peer_port_meta,
                     'port_is_connected': self.port.is_connected_to(self.peer_port_meta.port_id)},
                     peer_node_id=self.peer_port_meta.node_id, tb=True)
        if self.port.is_connected_to(self.peer_port_meta.port_id):
            # The other end beat us to connecting the port, lets just report success and return
            _log.analyze(self.node.id, "+ IS CONNECTED", {'local_port': self.port, 'peer_port': self.peer_port_meta},
                            peer_node_id=self.peer_port_meta.node_id)
            self.async_reply(status=response.CalvinResponse(True))
            return None

        if not status:
            # Failed getting a tunnel, just inform the one wanting to connect
            self.async_reply(status=response.CalvinResponse(response.INTERNAL_ERROR))
            return None
        # Finally we have all information and a tunnel
        # Lets ask the peer if it can connect our port.
        tunnel = self.token_tunnel.tunnels[self.peer_port_meta.node_id]
        _log.analyze(self.node.id, "+ SENDING",
                        {'local_port': self.port, 'peer_port': self.peer_port_meta,
                        'tunnel_status': self.token_tunnel.tunnels[self.peer_port_meta.node_id].status},
                        peer_node_id=self.peer_port_meta.node_id)

        self.node.proto.port_connect(callback=CalvinCB(self._connected_via_tunnel),
                                        port_id=self.port.id, port_properties=self.port.properties,
                                        peer_port_meta=self.peer_port_meta, tunnel_id=tunnel.id)

    def _connected_via_tunnel(self, reply):
        """ Gets called when remote responds to our request for port connection """
        _log.analyze(self.node.id, "+ " + str(reply), {'local_port': self.port, 'peer_port': self.peer_port_meta},
                            peer_node_id=self.peer_port_meta.node_id, tb=True)
        if reply in [response.BAD_REQUEST, response.NOT_FOUND, response.GATEWAY_TIMEOUT]:
            # Other end did not accept our port connection request
            if self.peer_port_meta.retries < 2 and self.peer_port_meta.node_id:
                # Maybe it is on another node now lets retry and lookup the port
                # FIXME: Could the port have moved to our node and we need to check local???
                self.peer_port_meta.retry(CalvinCB(self.connect))
                return
            self.async_reply(status=response.CalvinResponse(response.NOT_FOUND))
            return

        if reply == response.GONE:
            # Other end did not accept our port connection request, likely due to they have not got the message
            # about the tunnel in time
            _log.analyze(self.node.id, "+ RETRY", {'local_port': self.port, 'peer_port': self.peer_port_meta},
                            peer_node_id=self.peer_port_meta.node_id)
            if self.peer_port_meta.retries < 3:
                self.peer_port_meta.retries += 1
                # Status here just indicate that we should have a tunnel
                self._connect_via_tunnel(status=response.CalvinResponse(True))
            else:
                self.async_reply(status=response.CalvinResponse(False))
            return

        # Update our peer port's properties with newly recieved information
        if self.peer_port_meta.properties is None:
            self.peer_port_meta.properties = reply.data.get('port_properties', {})
        else:
            self.peer_port_meta.properties.update(reply.data.get('port_properties', {}))

        # Set up the port's endpoint
        tunnel = self.token_tunnel.tunnels[self.peer_port_meta.node_id]
        self.port.set_queue(queue.get(self.port, peer_port_meta=self.peer_port_meta))
        cls = endpoint.TunnelInEndpoint if self.port.direction == 'in' else endpoint.TunnelOutEndpoint
        endp = cls(self.port,
                   tunnel,
                   self.peer_port_meta.node_id,
                   reply.data['port_id'],
                   self.peer_port_meta.properties,
                   self.node.sched)

        invalid_endpoint = self.port.attach_endpoint(endp)
        invalid_endpoint.unregister(self.node.sched)
        invalid_endpoint.destroy()
        endp.register(self.node.sched)

        # Done connecting the port
        self.async_reply(status=response.CalvinResponse(True))

        # Update storage
        self.node.storage.add_port(self.port, self.node.id, self.port.owner.id)

    def connection_request(self):
        """ A request from a peer to connect a port"""
        _log.analyze(self.node.id, "+", self.kwargs, peer_node_id=self.peer_port_meta.node_id)
        try:
            payload = self.kwargs['payload']
        except:
            return response.CalvinResponse(False)
        if 'tunnel_id' not in payload:
            raise NotImplementedError()
        tunnel = self.token_tunnel.tunnels[self.peer_port_meta.node_id]
        if tunnel.id != payload['tunnel_id']:
            # For some reason does the tunnel id not match the one we have to connect to the peer
            # Likely due to that we have not yet received a tunnel request from the peer that replace our tunnel id
            # Can happen when race of simultaneous link setup and commands can be received out of order
            _log.analyze(self.node.id, "+ WRONG TUNNEL", payload, peer_node_id=self.peer_port_meta.node_id)
            return response.CalvinResponse(response.GONE)

        self.port.set_queue(queue.get(self.port, peer_port_meta=self.peer_port_meta))
        cls = endpoint.TunnelInEndpoint if self.port.direction == 'in' else endpoint.TunnelOutEndpoint
        endp = cls(self.port,
                   tunnel,
                   self.peer_port_meta.node_id,
                   self.peer_port_meta.port_id,
                   self.peer_port_meta.properties,
                   self.node.sched)

        invalid_endpoint = self.port.attach_endpoint(endp)
        invalid_endpoint.unregister(self.node.sched)
        invalid_endpoint.destroy()
        endp.register(self.node.sched)

        # Update storage
        self.node.storage.add_port(self.port, self.node.id, self.port.owner.id)

        _log.analyze(self.node.id, "+ OK", payload, peer_node_id=self.peer_port_meta.node_id)
        return response.CalvinResponse(response.OK, {'port_id': self.port.id, 'port_properties': self.port.properties})

    def disconnect(self, terminate=DISCONNECT.TEMPORARY):
        """ Obtain any missing information to enable disconnecting one port peer and make the disconnect"""

        _log.analyze(self.node.id, "+", {'port_id': self.port.id})
        # Disconnect and destroy the endpoints
        remaining_tokens = self._destroy_endpoints(terminate=terminate)
        self._serialize_remaining_tokens(remaining_tokens)

        terminate_peer = DISCONNECT.EXHAUST_PEER if terminate == DISCONNECT.EXHAUST else terminate
        # Inform peer port of disconnection
        self.node.proto.port_disconnect(callback=CalvinCB(self._disconnected_peer, terminate=terminate),
                                    port_id=self.port.id,
                                    peer_node_id=self.peer_port_meta.node_id,
                                    peer_port_id=self.peer_port_meta.port_id,
                                    terminate=terminate_peer,
                                    remaining_tokens=remaining_tokens)

    def _disconnected_peer(self, reply, terminate=DISCONNECT.TEMPORARY):
        """ Get called for each peer port when diconnecting but callback should only be called once"""
        try:
            # Remove this peer from the list of peer connections
            self._parallel_connections.remove(self)
        except:
            pass
        if not reply:
            # Got failed response do callback, but also inform
            # parallel connections that we have sent the callback
            self.parallel_set('sent_callback', True)
            if self.callback:
                _log.warning("Disconnect peer tunnel failed %s", str(reply))
                self.callback(status=reply, port_id=self.port.id)
                #self.callback(status=response.CalvinResponse(False), port_id=self.port.id)
            return
        try:
            remaining_tokens = reply.data['remaining_tokens']
            self._deserialize_remaining_tokens(remaining_tokens)
        except:
            _log.exception("Did not have remaining_tokens")
            remaining_tokens = {}
        self.port.exhausted_tokens(remaining_tokens)
        if terminate:
            self.node.storage.add_port(self.port, self.node.id, self.port.owner.id,
                                        exhausting_peers=remaining_tokens.keys())
        if not getattr(self, 'sent_callback', False) and not self._parallel_connections:
            # Last peer connection we should send OK
            if self.callback:
                self.callback(status=response.CalvinResponse(True), port_id=self.port.id)

    def _serialize_remaining_tokens(self, remaining_tokens):
        for peer_id, tokens in remaining_tokens.items():
            for token in tokens:
                token[1] = token[1].encode()

    def _deserialize_remaining_tokens(self, remaining_tokens):
        for peer_id, tokens in remaining_tokens.items():
            for token in tokens:
                token[1] = Token.decode(token[1])

    def disconnection_request(self, terminate=DISCONNECT.TEMPORARY, peer_remaining_tokens=None):
        """ A request from a peer to disconnect a port"""
        # Disconnect and destroy endpoints
        remaining_tokens = self._destroy_endpoints(terminate=terminate)
        self._deserialize_remaining_tokens(peer_remaining_tokens)
        self.port.exhausted_tokens(peer_remaining_tokens)
        if terminate:
            self.node.storage.add_port(self.port, self.node.id, self.port.owner.id,
                                        exhausting_peers=peer_remaining_tokens.keys())
        self._serialize_remaining_tokens(remaining_tokens)
        return response.CalvinResponse(True, {'remaining_tokens': remaining_tokens})

    def _destroy_endpoints(self, terminate=DISCONNECT.TEMPORARY):
        endpoints = self.port.disconnect(peer_ids=[self.peer_port_meta.port_id], terminate=terminate)
        _log.analyze(self.node.id, "+ EP", {'port_id': self.port.id, 'endpoints': endpoints})
        remaining_tokens = {}
        # Can only be one for the one peer as argument to disconnect, but loop for simplicity
        # FIXME: Let monitor handle whether it should be used or not
        for ep in endpoints:
            remaining_tokens.update(ep.remaining_tokens)
            ep.unregister(self.node.sched)
            ep.destroy()
        return remaining_tokens

    class TokenTunnel(object):
        """ Handles token transport over tunnel, common instance for all token tunnel connections """

        def __init__(self, node, pm):
            super(TunnelConnection.TokenTunnel, self).__init__()
            self.node = node
            self.pm = pm
            self.proto = node.proto
            # Register that we are interested in peer's requests for token transport tunnels
            self.proto.register_tunnel_handler('token', CalvinCB(self.tunnel_request_handles))
            self.tunnels = {}  # key: peer_node_id, value: tunnel instances
            self.pending_tunnels = {}  # key: peer_node_id, value: list of CalvinCB instances
            # Alias to port manager's port lookup
            self._get_local_port = self.pm._get_local_port

        def tunnel_request_handles(self, tunnel):
            """ Incoming tunnel request for token transport """
            # TODO check if we want a tunnel first
            self.tunnels[tunnel.peer_node_id] = tunnel
            tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
            tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
            tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
            # We accept it by returning True
            return True

        def tunnel_down(self, tunnel):
            """ Callback that the tunnel is not accepted or is going down """
            tunnel_peer_id = tunnel.peer_node_id
            try:
                self.tunnels.pop(tunnel_peer_id)
            except:
                pass

            # If a port connect have ordered a tunnel then it have a callback in pending
            # which want information on the failure
            if tunnel_peer_id in self.pending_tunnels:
                for cb in self.pending_tunnels[tunnel_peer_id]:
                    try:
                        cb(status=response.CalvinResponse(False))
                    except:
                        pass
                self.pending_tunnels.pop(tunnel_peer_id)
            # We should always return True which sends an OK on the destruction of the tunnel
            return True

        def tunnel_up(self, tunnel):
            """ Callback that the tunnel is working """
            tunnel_peer_id = tunnel.peer_node_id
            # If a port connect have ordered a tunnel then it have a callback in pending
            # which want to continue with the connection
            if tunnel_peer_id in self.pending_tunnels:
                for cb in self.pending_tunnels[tunnel_peer_id]:
                    try:
                        cb(status=response.CalvinResponse(True))
                    except:
                        pass
                self.pending_tunnels.pop(tunnel_peer_id)

        def recv_token_handler(self, tunnel, payload):
            """ Gets called when a token arrives on any port """
            try:
                port = self._get_local_port(port_id=payload['peer_port_id'])
                for e in port.endpoints:
                    # We might have started a disconnect, just ignore in that case
                    # it is sorted out if we connect again
                    try:
                        if e.peer_id == payload['port_id']:
                            e.recv_token(payload)
                            break
                    except:
                        pass
            except:
                # Inform other end that it sent token to a port that does not exist on this node or
                # that we have initiated a disconnect (endpoint does not have recv_token).
                # Can happen e.g. when the actor and port just migrated and the token was in the air
                _log.debug("recv_token_handler, ABORT")
                reply = {'cmd': 'TOKEN_REPLY',
                         'port_id': payload['port_id'],
                         'peer_port_id': payload['peer_port_id'],
                         'sequencenbr': payload['sequencenbr'],
                         'value': 'ABORT'}
                tunnel.send(reply)

        def recv_token_reply_handler(self, tunnel, payload):
            """ Gets called when a token is (N)ACKed for any port """
            try:
                port = self._get_local_port(port_id=payload['port_id'])
            except:
                pass
            else:
                # Send the reply to correct endpoint (an outport may have several when doing fan-out)
                for e in port.endpoints:
                    # We might have started disconnect before getting the reply back, just ignore in that case
                    # it is sorted out if we connect again
                    try:
                        if e.get_peer()[1] == payload['peer_port_id']:
                            e.reply(payload['sequencenbr'], payload['value'])
                            break
                    except:
                        pass

        def tunnel_recv_handler(self, tunnel, payload):
            """ Gets called when we receive a message over a tunnel """
            if 'cmd' in payload:
                if 'TOKEN' == payload['cmd']:
                    self.recv_token_handler(tunnel, payload)
                elif 'TOKEN_REPLY' == payload['cmd']:
                    self.recv_token_reply_handler(tunnel, payload)

    def init(self):
        return TunnelConnection.TokenTunnel(self.node, self.kwargs['portmanager'])
