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
from calvin.utilities.utils import enum
from calvin.runtime.south import endpoint
from calvin.runtime.north.calvin_proto import CalvinTunnel
from calvin.runtime.north.plugins.port import queue
from calvin.actor.actorport import PortMeta
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


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

    PURPOSE = enum('INIT', 'CONNECT', 'DISCONNECT')

    def get(self, port, peer_port_meta, callback=None, **kwargs):
        if peer_port_meta.is_local():
            return LocalConnection(self.node, self.purpose, port, peer_port_meta, callback, **kwargs)
        elif self.purpose == self.PURPOSE.DISCONNECT and peer_port_meta.node_id is None:
            # A port that miss node info that we want to disconnect is already disconnected
            return Disconnected(self.node, self.purpose, port, peer_port_meta, callback, **kwargs)
        else:
            # Remote connection
            # TODO Currently we only have support for setting up a remote connection via tunnel
            return TunnelConnection(self.node, self.purpose, port, peer_port_meta, callback, **kwargs)

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
        return connections

    def init(self):
        data = {}
        for C in _connection_classes:
            data[C.__name__] = C(self.node, self.PURPOSE.INIT, None, None, None, **self.kwargs).init()
        return data


class BaseConnection(object):
    """BaseConnection"""

    def __init__(self, node, purpose, port, peer_port_meta, callback, *args, **kwargs):
        super(BaseConnection, self).__init__()
        self.node = node
        self.purpose = purpose
        self.port = port
        self.peer_port_meta = peer_port_meta
        self.callback = callback
        self._parallel_connections = []

    def parallel_connections(self, connections):
        self._parallel_connections = connections

    def parallel_set(self, key, value):
        for c in self._parallel_connections:
            setattr(c, key, value)

    def init(self):
        return None

    def __str__(self):
        return "%s(port_id=%s, peer_port_id=%s)" % (self.__class__.__name__, self.port.id, self.peer_port_meta.port_id)


class Disconnected(BaseConnection):
    """ When a peer already is disconnected """

    def __init__(self, node, purpose, port, peer_port_meta, callback, **kwargs):
        super(Disconnected, self).__init__(node, purpose, port, peer_port_meta, callback)
        self.kwargs = kwargs

    def disconnect(self):
        if self.callback:
            self.callback(status=response.CalvinResponse(True), port_id=self.port.id)


class LocalConnection(BaseConnection):
    """ Connect two ports that are local"""

    def __init__(self, node, purpose, port, peer_port_meta, callback, **kwargs):
        super(LocalConnection, self).__init__(node, purpose, port, peer_port_meta, callback)
        self.kwargs = kwargs

    def connect(self):
        _log.analyze(self.node.id, "+ LOCAL", {'local_port': self.port, 'peer_port': self.peer_port_meta},
                        peer_node_id=self.peer_port_meta.node_id)
        port1 = self.port
        port2 = self.peer_port_meta.port
        # Local connect wants the first port to be an inport
        inport, outport = (port1, port2) if port1.direction == 'in' else (port2, port1)
        self._connect_via_local(inport, outport)
        if self.callback:
            self.callback(status=response.CalvinResponse(True),
                     actor_id=self.port.owner.id,
                     port_name=self.port.name,
                     port_id=self.port.id,
                     peer_node_id=self.peer_port_meta.node_id,
                     peer_actor_id=self.peer_port_meta.actor_id,
                     peer_port_name=self.peer_port_meta.port_name,
                     peer_port_id=self.peer_port_meta.port_id)
        return None

    def _connect_via_local(self, inport, outport):
        """ Both connecting ports are local, just connect them """
        _log.analyze(self.node.id, "+", {})
        inport.set_queue(queue.get(inport, peer_port=outport))
        outport.set_queue(queue.get(outport, peer_port=inport))
        ein = endpoint.LocalInEndpoint(inport, outport)
        eout = endpoint.LocalOutEndpoint(outport, inport)

        if ein.use_monitor():
            self.node.monitor.register_endpoint(ein)
        if eout.use_monitor():
            self.node.monitor.register_endpoint(eout)

        invalid_endpoint = outport.attach_endpoint(eout)
        if invalid_endpoint:
            if invalid_endpoint.use_monitor():
                self.node.monitor.unregister_endpoint(invalid_endpoint)
            invalid_endpoint.destroy()

        # Must attach in endpoint after out endpoint since starts with
        # removing tokens transfered but with unhandled ACKs by the out
        # endpoint
        invalid_endpoint = inport.attach_endpoint(ein)
        if invalid_endpoint:
            if invalid_endpoint.use_monitor():
                self.node.monitor.unregister_endpoint(invalid_endpoint)
            invalid_endpoint.destroy()

        # Update storage
        self.node.storage.add_port(inport, self.node.id, inport.owner.id)
        self.node.storage.add_port(outport, self.node.id, outport.owner.id)

    def disconnect(self):
        """ Obtain any missing information to enable disconnecting one peer port and make the disconnect"""

        _log.analyze(self.node.id, "+", {'port_id': self.port.id})
        endpoints = self.port.disconnect(peer_ids=[self.peer_port_meta.port_id])
        _log.analyze(self.node.id, "+ EP", {'port_id': self.port.id, 'endpoints': endpoints})
        # Should only be one but maybe future ports will have multiple endpoints for a peer
        for ep in endpoints:
            if ep.use_monitor():
                self.node.monitor.unregister_endpoint(ep)
            ep.destroy()
        _log.analyze(self.node.id, "+ EP DESTROYED", {'port_id': self.port.id})

        # Disconnect other end also, which is also local
        endpoints = self.peer_port_meta.port.disconnect(peer_ids=[self.port.id])
        _log.analyze(self.node.id, "+ EP PEER", {'port_id': self.port.id, 'endpoints': endpoints})
        # Should only be one but maybe future ports will have multiple endpoints for a peer
        for ep in endpoints:
            if ep.use_monitor():
                self.node.monitor.unregister_endpoint(ep)
            ep.destroy()
        _log.analyze(self.node.id, "+ DISCONNECTED", {'port_id': self.port.id})

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


class TunnelConnection(BaseConnection):
    """ Connect two ports that are remote over a Tunnel"""

    def __init__(self, node, purpose, port, peer_port_meta, callback, **kwargs):
        super(TunnelConnection, self).__init__(node, purpose, port, peer_port_meta, callback)
        self.kwargs = kwargs
        if self.purpose != ConnectionFactory.PURPOSE.INIT:
            self.token_tunnel = self.node.pm.connections_data[self.__class__.__name__]

    def connect(self):
        tunnel = None
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
        elif tunnel.status == CalvinTunnel.STATUS.TERMINATED:
            # TODO should we retry at this level?
            if self.callback:
                self.callback(status=response.CalvinResponse(response.INTERNAL_ERROR),
                         actor_id=self.port.owner.id,
                         port_name=self.port.name,
                         port_id=self.port.id,
                         peer_node_id=self.peer_port_meta.node_id,
                         peer_actor_id=self.peer_port_meta.actor_id,
                         peer_port_name=self.peer_port_meta.port_name,
                         peer_port_id=self.peer_port_meta.port_id)
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
            if self.callback:
                self.callback(status=response.CalvinResponse(True),
                         actor_id=self.port.owner.id,
                         port_name=self.port.name,
                         port_id=self.port.id,
                         peer_node_id=self.peer_port_meta.node_id,
                         peer_actor_id=self.peer_port_meta.actor_id,
                         peer_port_name=self.peer_port_meta.port_name,
                         peer_port_id=self.peer_port_meta.port_id)
            return None

        if not status:
            # Failed getting a tunnel, just inform the one wanting to connect
            if self.callback:
                self.callback(status=response.CalvinResponse(response.INTERNAL_ERROR),
                         actor_id=self.port.owner.id,
                         port_name=self.port.name,
                         port_id=self.port.id,
                         peer_node_id=self.peer_port_meta.node_id,
                         peer_actor_id=self.peer_port_meta.actor_id,
                         peer_port_name=self.peer_port_meta.port_name,
                         peer_port_id=self.peer_port_meta.port_id)
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
            if self.callback:
                self.callback(status=response.CalvinResponse(response.NOT_FOUND),
                         actor_id=self.port.owner.id,
                         port_name=self.port.name,
                         port_id=self.port.id,
                         peer_node_id=self.peer_port_meta.node_id,
                         peer_actor_id=self.peer_port_meta.actor_id,
                         peer_port_name=self.peer_port_meta.port_name,
                         peer_port_id=self.peer_port_meta.port_id)
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
                return
            else:
                if self.callback:
                    self.callback(status=response.CalvinResponse(False),
                                     actor_id=self.port.owner.id,
                                     port_name=self.port.name,
                                     port_id=self.port.id,
                                     peer_node_id=self.peer_port_meta.node_id,
                                     peer_actor_id=self.peer_port_meta.actor_id,
                                     peer_port_name=self.peer_port_meta.port_name,
                                     peer_port_id=self.peer_port_meta.port_id)
                return

        # Set up the port's endpoint
        tunnel = self.token_tunnel.tunnels[self.peer_port_meta.node_id]
        self.port.set_queue(queue.get(self.port, peer_port_meta=self.peer_port_meta))
        if self.port.direction == 'in':
            endp = endpoint.TunnelInEndpoint(self.port,
                                             tunnel,
                                             self.peer_port_meta.node_id,
                                             reply.data['port_id'],
                                             self.node.sched.trigger_loop)
        else:
            endp = endpoint.TunnelOutEndpoint(self.port,
                                              tunnel,
                                              self.peer_port_meta.node_id,
                                              reply.data['port_id'],
                                              self.node.sched.trigger_loop)
        if endp.use_monitor():
            # register into main loop
            self.node.monitor.register_endpoint(endp)
        invalid_endpoint = self.port.attach_endpoint(endp)
        # remove previous endpoint
        if invalid_endpoint:
            if invalid_endpoint.use_monitor():
                self.monitor.unregister_endpoint(invalid_endpoint)
            invalid_endpoint.destroy()

        # Done connecting the port
        if self.callback:
            self.callback(status=response.CalvinResponse(True),
                             actor_id=self.port.owner.id,
                             port_name=self.port.name,
                             port_id=self.port.id,
                             peer_node_id=self.peer_port_meta.node_id,
                             peer_actor_id=self.peer_port_meta.actor_id,
                             peer_port_name=self.peer_port_meta.port_name,
                             peer_port_id=self.peer_port_meta.port_id)

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
        if self.port.direction == "in":
            endp = endpoint.TunnelInEndpoint(self.port,
                                             tunnel,
                                             self.peer_port_meta.node_id,
                                             self.peer_port_meta.port_id,
                                             self.node.sched.trigger_loop)
        else:
            endp = endpoint.TunnelOutEndpoint(self.port,
                                              tunnel,
                                              self.peer_port_meta.node_id,
                                              self.peer_port_meta.port_id,
                                              self.node.sched.trigger_loop)
        if endp.use_monitor():
            self.node.monitor.register_endpoint(endp)

        invalid_endpoint = self.port.attach_endpoint(endp)
        # Remove previous endpoint
        if invalid_endpoint:
            if invalid_endpoint.use_monitor():
                self.monitor.unregister_endpoint(invalid_endpoint)
            invalid_endpoint.destroy()

        # Update storage
        self.node.storage.add_port(self.port, self.node.id, self.port.owner.id)

        _log.analyze(self.node.id, "+ OK", payload, peer_node_id=self.peer_port_meta.node_id)
        return response.CalvinResponse(response.OK, {'port_id': self.port.id})

    def disconnect(self):
        """ Obtain any missing information to enable disconnecting one port peer and make the disconnect"""

        _log.analyze(self.node.id, "+", {'port_id': self.port.id})
        # Disconnect and destroy the endpoints
        self._destroy_endpoints()

        # Inform peer port of disconnection
        self.node.proto.port_disconnect(callback=CalvinCB(self._disconnected_peer),
                                    port_id=self.port.id,
                                    peer_node_id=self.peer_port_meta.node_id,
                                    peer_port_id=self.peer_port_meta.port_id)

    def _disconnected_peer(self, reply):
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
                self.callback(status=response.CalvinResponse(False), port_id=self.port.id)
        if not getattr(self, 'sent_callback', False) and not self._parallel_connections:
            # Last peer connection we should send OK
            if self.callback:
                self.callback(status=response.CalvinResponse(True), port_id=self.port.id)

    def disconnection_request(self):
        """ A request from a peer to disconnect a port"""
        # Disconnect and destroy endpoints
        self._destroy_endpoints()
        return response.CalvinResponse(True)

    def _destroy_endpoints(self):
        endpoints = self.port.disconnect(peer_ids=[self.peer_port_meta.port_id])
        _log.analyze(self.node.id, "+ EP", {'port_id': self.port.id, 'endpoints': endpoints})
        # Should only be one but maybe future ports will have multiple endpoints for a peer
        for ep in endpoints:
            if ep.use_monitor():
                self.node.monitor.unregister_endpoint(ep)
            ep.destroy()

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
                port.endpoint.recv_token(payload)
            except:
                # Inform other end that it sent token to a port that does not exist on this node or
                # that we have initiated a disconnect (endpoint does not have recv_token).
                # Can happen e.g. when the actor and port just migrated and the token was in the air
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


# All connection classes
_connection_classes = [LocalConnection, TunnelConnection]
