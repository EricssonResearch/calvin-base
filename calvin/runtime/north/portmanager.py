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

from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.south import endpoint
from calvin.runtime.north.calvin_proto import CalvinTunnel
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinlogger
from calvin.actor.actor import ShadowActor

_log = calvinlogger.get_logger(__name__)


class PortMeta(object):
    """ Collection and retrieval of meta data for a port """
    def __init__(self, port_manager, actor_id=None, port_id=None, port_name=None, properties=None, node_id=None):
        super(PortMeta, self).__init__()
        self.pm = port_manager
        self.actor_id = actor_id
        self.port_id = port_id
        self.port_name = port_name
        self.properties = properties
        self.node_id = node_id
        self._port = None
        self.retries = 0  # Used to keep track of how many times we have tried to find the port

    def encode(self):
        return {    'actor_id': self.actor_id,
                    'port_id': self.port_id,
                    'port_name': self.port_name,
                    'properties': self.properties,
                    'node_id': self.node_id
                }

    def __str__(self):
        return str(self.encode())

    def get_local_port(self):
        self.retrieve(callback=None, local_only=True)
        return self._port

    def is_local(self):
        return self.node_id == self.pm.node.id

    def retry(self, callback):
        self.node_id = None
        self.retries += 1
        self.retrieve(callback)

    def retrieve(self, callback=None, local_only=False):
        """ Try to fill in port meta information based on current
            available info. Raise CalvinResponseException (BAD_REQUEST)
            when the supplied input data is incomplete.
            Could also return OK (directly available) or
            ACCEPTED (maybe available in callback).
            When not a BAD_REQUEST the callback will be called with
            any result.

            Will only make sure that either port id or
            (actor name, port name, direction) is available.
            Node id is always retrieved.
            local_only means only looks locally for the port.
        """
        try:
            direction = self.properties['direction']
        except:
            direction = None
        try:
            self._port = self.pm._get_local_port(self.actor_id, self.port_name, direction, self.port_id)
            # Found locally
            self.actor_id = self._port.owner.id
            self.port_id = self._port.id
            self.port_name = self._port.name
            self.properties = self._port.properties
            self.node_id = self.pm.node.id
            status = response.CalvinResponse(True)
            if callback:
                callback(status=status, port_meta=self)
            return status
        except:
            # not local
            if local_only:
                if self.port_id:
                    status = response.CalvinResponse(response.BAD_REQUEST,
                                                    "Port %s must be local" % (self.port_id))
                else:
                    status = response.CalvinResponse(response.BAD_REQUEST,
                                                    "Port %s on actor %s must be local" %
                                                    (self.port_name, self.actor_id))
                raise response.CalvinResponseException(status)

        # No node id ...
        if not self.node_id:
            if self.port_id:
                # ... but an id of a port lets ask for more info
                self.pm.node.storage.get_port(self.port_id, CalvinCB(self._retrieve_by_port_id,
                                                                        cb=callback))
                return response.CalvinResponse(response.ACCEPTED)
            elif self.actor_id and self.port_name:
                # ... but an id of an actor lets ask for more info
                self.pm.node.storage.get_actor(self.actor_id, CalvinCB(self._retrieve_by_actor_id,
                                                                        cb=callback))
                return response.CalvinResponse(response.ACCEPTED)
            else:
                # ... and no info on how to get more info, abort
                status=response.CalvinResponse(response.BAD_REQUEST,
                        "Unknown node id (%s), actor_id (%s) and/or port_id(%s)" % 
                        (self.node_id, self.actor_id, self.port_id))
                raise response.CalvinResponseException(status)

        # Have node id but are we missing port info
        if not ((self.actor_id and self.port_name and direction) or self.port_id):
                # We miss information on to find the peer port
                status=response.CalvinResponse(response.BAD_REQUEST,
                        "actor_id (%s) and/or port_id(%s)" % 
                        (self.actor_id, self.port_id))
                raise response.CalvinResponseException(status)

        # Got everything for an answer
        status = response.CalvinResponse(True)
        if callback:
            callback(status=status, port_meta=self)
        return status

    def _retrieve_by_port_id(self, key, value, cb):
        """ Gets called when registry responds with port information """
        _log.analyze(self.pm.node.id, "+", self.encode(), peer_node_id=self.node_id, tb=True)
        if not isinstance(value, dict):
            if cb:
                cb(status=response.CalvinResponse(response.NOT_FOUND, "Port unknown in registry"), port_meta=self)
            return
        try:
            self.node_id = value['node_id'] or self.node_id
        except:
            if not self.node_id:
                if cb:
                    cb(status=response.CalvinResponse(response.NOT_FOUND, "Port have unknown node in registry"),
                        port_meta=self)
                return

        # Got everything for an answer
        if cb:
            cb(status=response.CalvinResponse(True), port_meta=self)

    def _retrieve_by_actor_id(self, key, value, cb):
        """ Gets called when registry responds with actor information"""
        _log.analyze(self.pm.node.id, "+", self.encode(), peer_node_id=self.node_id, tb=True)
        if not isinstance(value, dict):
            if cb:
                cb(status=response.CalvinResponse(response.NOT_FOUND, "Actor unknown in registry"), port_meta=self)
            return

        try:
            self.node_id = value['node_id'] or self.node_id
        except:
            if not self.node_id:
                if cb:
                    cb(status=response.CalvinResponse(response.NOT_FOUND, "Port have unknown node in registry"),
                        port_meta=self)
                return

        if not self.port_id:
            try:
                # Get port id based on names
                ports = value['inports' if self.properties['direction'] == 'in' else 'outports']
                for port in ports:
                    if port['name'] == self.port_name:
                        self.port_id = port['id']
                        break
            except:
                if not self.node_id:
                    if cb:
                        cb(status=response.CalvinResponse(response.NOT_FOUND, "Port have unknown id in registry"),
                            port_meta=self)
                    return

        # Got everything for an answer
        if cb:
            cb(status=response.CalvinResponse(True), port_meta=self)


class PortManager(object):
    """
    PortManager handles the setup of communication between ports intra- & inter-runtimes
    """

    def __init__(self, node, proto):
        super(PortManager, self).__init__()
        self.node = node
        self.monitor = self.node.monitor
        self.proto = proto
        # Register that we are interested in peer's requests for token transport tunnels
        self.proto.register_tunnel_handler('token', CalvinCB(self.tunnel_request_handles))
        self.tunnels = {} # key: peer_node_id, value: tunnel instances
        self.ports = {} # key: port_id, value: port
        self.pending_tunnels = {} # key: peer_node_id, value: list of CalvinCB instances
        self.disconnecting_ports={} # key: port_id, value: list of peer port ids that are disconnecting and waiting for ack

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
                     'port_id':payload['port_id'],
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

    def connection_request(self, payload):
        """ A request from a peer to connect a port"""
        _log.analyze(self.node.id, "+", payload, peer_node_id=payload['from_rt_uuid'])
        if not ('peer_port_id' in payload or
                ('peer_actor_id' in payload and
                'peer_port_name' in payload and
                'peer_port_dir' in payload)):
            # Not enough info to find port
            _log.analyze(self.node.id, "+ NOT ENOUGH DATA", payload, peer_node_id=payload['from_rt_uuid'])
            return response.CalvinResponse(response.BAD_REQUEST)
        try:
            port = self._get_local_port(payload['peer_actor_id'],
                                        payload['peer_port_name'],
                                        payload['peer_port_dir'],
                                        payload['peer_port_id'])
        except:
            # We don't have the port
            _log.analyze(self.node.id, "+ PORT NOT FOUND", payload, peer_node_id=payload['from_rt_uuid'])
            return response.CalvinResponse(response.NOT_FOUND)
        else:
            if not 'tunnel_id' in payload:
                # TODO implement connection requests not via tunnel
                raise NotImplementedError()
            tunnel = self.tunnels[payload['from_rt_uuid']]
            if tunnel.id != payload['tunnel_id']:
                # For some reason does the tunnel id not match the one we have to connect to the peer
                # Likely due to that we have not yet received a tunnel request from the peer that replace our tunnel id
                # Can happen when race of simultaneous link setup and commands can be received out of order
                _log.analyze(self.node.id, "+ WRONG TUNNEL", payload, peer_node_id=payload['from_rt_uuid'])
                return response.CalvinResponse(response.GONE)

            if port.direction == "in":
                endp = endpoint.TunnelInEndpoint(port,
                                                 tunnel,
                                                 payload['from_rt_uuid'],
                                                 payload['port_id'],
                                                 self.node.sched.trigger_loop)
            else:
                endp = endpoint.TunnelOutEndpoint(port,
                                                  tunnel,
                                                  payload['from_rt_uuid'],
                                                  payload['port_id'],
                                                  self.node.sched.trigger_loop)
                self.monitor.register_out_endpoint(endp)

            invalid_endpoint = port.attach_endpoint(endp)
            # Remove previous endpoint
            if invalid_endpoint:
                if isinstance(invalid_endpoint, endpoint.TunnelOutEndpoint):
                    self.monitor.unregister_out_endpoint(invalid_endpoint)
                invalid_endpoint.destroy()

            # Update storage
            if port.direction == "in":
                self.node.storage.add_port(port, self.node.id, port.owner.id, "in")
            else:
                self.node.storage.add_port(port, self.node.id, port.owner.id, "out")

            _log.analyze(self.node.id, "+ OK", payload, peer_node_id=payload['from_rt_uuid'])
            return response.CalvinResponse(response.OK, {'port_id': port.id})


    def connect(self, callback=None, actor_id=None, port_name=None, port_dir=None, port_id=None, peer_node_id=None,
                      peer_actor_id=None, peer_port_name=None, peer_port_dir=None, peer_port_id=None):
        """ Obtain any missing information to enable making a connection and make actual connect
            callback: an optional callback that gets called with status when finished
            local port identified by:
                actor_id, port_name and port_dir='in'/'out' or
                port_id
            peer_node_id: an optional node id the peer port is locate on, will use storage to find it if not supplied
            peer port (remote or local) identified by:
                peer_actor_id, peer_port_name and peer_port_dir='in'/'out' or
                peer_port_id

            connect -----------------------------> _connect -> _connect_via_tunnel -> _connected_via_tunnel -!
                                                            \-> _connect_via_local -!
        """

        local_port_meta = PortMeta(self, actor_id=actor_id, port_id=port_id, port_name=port_name,
                            properties={'direction': port_dir}, node_id=self.node.id)
        peer_port_meta = PortMeta(self, actor_id=peer_actor_id, port_id=peer_port_id, port_name=peer_port_name,
                            properties={'direction': peer_port_dir}, node_id=peer_node_id)

        _log.analyze(self.node.id, "+", {'local': local_port_meta, 'peer': peer_port_meta},
                    peer_node_id=peer_node_id, tb=True)
        try:
            port = local_port_meta.get_local_port()
        except response.CalvinResponseException as e:
            if callback:
                callback(status=e.response,
                         actor_id=actor_id,
                         port_name=port_name,
                         port_id=port_id,
                         peer_node_id=peer_node_id,
                         peer_actor_id=peer_actor_id,
                         peer_port_name=peer_port_name,
                         peer_port_id=peer_port_id)
                return
            else:
                raise e.response

        # Retrieve node id etc, raise exception if not possible, continue in _connect otherwise 
        try:
            peer_port_meta.retrieve(callback=CalvinCB(self._connect, local_port=port, callback=callback))
        except response.CalvinResponseException as e:
            if callback:
                callback(status=e.response,
                         actor_id=actor_id,
                         port_name=port_name,
                         port_id=port_id,
                         peer_node_id=peer_node_id,
                         peer_actor_id=peer_actor_id,
                         peer_port_name=peer_port_name,
                         peer_port_id=peer_port_id)
                return
            else:
                raise e.response

    def _connect(self, local_port=None, callback=None, status=None, port_meta=None):
        """ Do the connection of ports, all neccessary information supplied but
            maybe not all pre-requisites for remote connections.
        """
        if not status:
            if callback:
                callback(status=status,
                         actor_id=local_port.owner.id,
                         port_name=local_port.name,
                         port_id=local_port.id,
                         peer_node_id=port_meta.node_id,
                         peer_actor_id=port_meta.actor_id,
                         peer_port_name=port_meta.port_name,
                         peer_port_id=port_meta.port_id)
            return
        _log.analyze(self.node.id, "+", {'local_port': local_port, 'peer_port': port_meta},
                        peer_node_id=port_meta.node_id, tb=True)
        # Local connect
        if port_meta.is_local():
            _log.analyze(self.node.id, "+ LOCAL", {'local_port': local_port, 'peer_port': port_meta},
                            peer_node_id=port_meta.node_id)
            port1 = local_port
            port2 = port_meta.get_local_port()
            # Local connect wants the first port to be an inport
            inport , outport = (port1, port2) if port1.direction=='in' else (port2, port1)
            self._connect_via_local(inport, outport)
            if callback:
                callback(status=response.CalvinResponse(True) ,
                         actor_id=local_port.owner.id,
                         port_name=local_port.name,
                         port_id=local_port.id,
                         peer_node_id=port_meta.node_id,
                         peer_actor_id=port_meta.actor_id,
                         peer_port_name=port_meta.port_name,
                         peer_port_id=port_meta.port_id)
            return None

        # Remote connection
        # TODO Currently we only have support for setting up a remote connection via tunnel
        tunnel = None
        if not port_meta.node_id in self.tunnels.iterkeys():
            # No tunnel to peer, get one first
            _log.analyze(self.node.id, "+ GET TUNNEL", port_meta, peer_node_id=port_meta.node_id)
            tunnel = self.proto.tunnel_new(port_meta.node_id, 'token', {})
            tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
            tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
            tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
            self.tunnels[port_meta.node_id] = tunnel
        else:
            tunnel = self.tunnels[port_meta.node_id]

        if tunnel.status == CalvinTunnel.STATUS.PENDING:
            if not port_meta.node_id in self.pending_tunnels:
                self.pending_tunnels[port_meta.node_id] = []
            # call _connect_via_tunnel when we get the response of the tunnel
            self.pending_tunnels[port_meta.node_id].append(CalvinCB(self._connect_via_tunnel,
                        local_port=local_port,
                        port_meta=port_meta,
                        callback=callback))
            return
        elif tunnel.status == CalvinTunnel.STATUS.TERMINATED:
            # TODO should we retry at this level?
            if callback:
                callback(status=response.CalvinResponse(response.INTERNAL_ERROR), 
                         actor_id=local_port.owner.id,
                         port_name=local_port.name,
                         port_id=local_port.id,
                         peer_node_id=port_meta.node_id,
                         peer_actor_id=port_meta.actor_id,
                         peer_port_name=port_meta.port_name,
                         peer_port_id=port_meta.port_id)
            return

        _log.analyze(self.node.id, "+ HAD TUNNEL", {'local_port': local_port, 'peer_port': port_meta,
                                                    'tunnel_status': self.tunnels[port_meta.node_id].status},
                        peer_node_id=port_meta.node_id)
        self._connect_via_tunnel(status=response.CalvinResponse(True), local_port=local_port,
                                    port_meta=port_meta, callback=callback)

    def _connect_via_tunnel(self, status=None, local_port=None, port_meta=None, callback=None):
        """ All information and hopefully (status OK) a tunnel to the peer is available for a port connect"""
        _log.analyze(self.node.id, "+ " + str(status),
                     {'local_port': local_port, 'peer_port': port_meta,
                     'port_is_connected': local_port.is_connected_to(port_meta.port_id)},
                     peer_node_id=port_meta.node_id, tb=True)
        if local_port.is_connected_to(port_meta.port_id):
            # The other end beat us to connecting the port, lets just report success and return
            _log.analyze(self.node.id, "+ IS CONNECTED", {'local_port': local_port, 'peer_port': port_meta},
                            peer_node_id=port_meta.node_id)
            if callback:
                callback(status=response.CalvinResponse(True), 
                         actor_id=local_port.owner.id,
                         port_name=local_port.name,
                         port_id=local_port.id,
                         peer_node_id=port_meta.node_id,
                         peer_actor_id=port_meta.actor_id,
                         peer_port_name=port_meta.port_name,
                         peer_port_id=port_meta.port_id)
            return None

        if not status:
            # Failed getting a tunnel, just inform the one wanting to connect
            if callback:
                callback(status=response.CalvinResponse(response.INTERNAL_ERROR),
                         actor_id=local_port.owner.id,
                         port_name=local_port.name,
                         port_id=local_port.id,
                         peer_node_id=port_meta.node_id,
                         peer_actor_id=port_meta.actor_id,
                         peer_port_name=port_meta.port_name,
                         peer_port_id=port_meta.port_id)
                return None
        # Finally we have all information and a tunnel
        # Lets ask the peer if it can connect our port.
        tunnel = self.tunnels[port_meta.node_id]
        _log.analyze(self.node.id, "+ SENDING", {'local_port': local_port, 'peer_port': port_meta,
                                                    'tunnel_status': self.tunnels[port_meta.node_id].status},
                        peer_node_id=port_meta.node_id)

        self.proto.port_connect(callback=CalvinCB(self._connected_via_tunnel, local_port=local_port,
                                                    port_meta=port_meta, callback=callback),
                                port_id=local_port.id, peer_port_meta=port_meta, tunnel=tunnel)


    def _connected_via_tunnel(self, reply, local_port=None, port_meta=None, callback=None):
        """ Gets called when remote responds to our request for port connection """
        _log.analyze(self.node.id, "+ " + str(reply), {'local_port': local_port, 'peer_port': port_meta},
                            peer_node_id=port_meta.node_id, tb=True)
        if reply in [response.BAD_REQUEST, response.NOT_FOUND, response.GATEWAY_TIMEOUT]:
            # Other end did not accept our port connection request
            if port_meta.retries < 2 and port_meta.node_id:
                # Maybe it is on another node now lets retry and lookup the port
                port_meta.retry(CalvinCB(self._connect, local_port=local_port, callback=callback, port_meta=port_meta))
                return
            if callback:
                callback(status=response.CalvinResponse(response.NOT_FOUND),
                         actor_id=local_port.owner.id,
                         port_name=local_port.name,
                         port_id=local_port.id,
                         peer_node_id=port_meta.node_id,
                         peer_actor_id=port_meta.actor_id,
                         peer_port_name=port_meta.port_name,
                         peer_port_id=port_meta.port_id)
                return

        if reply == response.GONE:
            # Other end did not accept our port connection request, likely due to they have not got the message
            # about the tunnel in time
            _log.analyze(self.node.id, "+ RETRY", {'local_port': local_port, 'peer_port': port_meta},
                            peer_node_id=port_meta.node_id)
            if port_meta.retries < 3:
                port_meta.retries += 1
                # Status here just indicate that we should have a tunnel
                self._connect_via_tunnel(status=response.CalvinResponse(True),
                                        local_port=local_port, callback=callback, port_meta=port_meta)
                return
            else:
                if callback:
                    callback(status=response.CalvinResponse(False),
                             actor_id=local_port.owner.id,
                             port_name=local_port.name,
                             port_id=local_port.id,
                             peer_node_id=port_meta.node_id,
                             peer_actor_id=port_meta.actor_id,
                             peer_port_name=port_meta.port_name,
                             peer_port_id=port_meta.port_id)
                return

        # Set up the port's endpoint
        tunnel = self.tunnels[port_meta.node_id]
        if local_port.direction == 'in':
            endp = endpoint.TunnelInEndpoint(local_port,
                                             tunnel,
                                             port_meta.node_id,
                                             reply.data['port_id'],
                                             self.node.sched.trigger_loop)
        else:
            endp = endpoint.TunnelOutEndpoint(local_port,
                                              tunnel,
                                              port_meta.node_id,
                                              reply.data['port_id'],
                                              self.node.sched.trigger_loop)
            # register into main loop
            self.monitor.register_out_endpoint(endp)
        invalid_endpoint = local_port.attach_endpoint(endp)
        # remove previous endpoint
        if invalid_endpoint:
            if isinstance(invalid_endpoint, endpoint.TunnelOutEndpoint):
                self.monitor.unregister_out_endpoint(invalid_endpoint)
            invalid_endpoint.destroy()

        # Done connecting the port
        if callback:
            callback(status=response.CalvinResponse(True),
                     actor_id=local_port.owner.id,
                     port_name=local_port.name,
                     port_id=local_port.id,
                     peer_node_id=port_meta.node_id,
                     peer_actor_id=port_meta.actor_id,
                     peer_port_name=port_meta.port_name,
                     peer_port_id=port_meta.port_id)

        # Update storage
        if local_port.direction == 'in':
            self.node.storage.add_port(local_port, self.node.id, local_port.owner.id, "in")
        else:
            self.node.storage.add_port(local_port, self.node.id, local_port.owner.id, "out")


    def _connect_via_local(self, inport, outport):
        """ Both connecting ports are local, just connect them """
        _log.analyze(self.node.id, "+", {})
        ein = endpoint.LocalInEndpoint(inport, outport)
        eout = endpoint.LocalOutEndpoint(outport, inport)

        invalid_endpoint = inport.attach_endpoint(ein)
        if invalid_endpoint:
            invalid_endpoint.destroy()

        invalid_endpoint = outport.attach_endpoint(eout)
        if invalid_endpoint:
            if isinstance(invalid_endpoint, endpoint.TunnelOutEndpoint):
                self.monitor.unregister_out_endpoint(invalid_endpoint)
            invalid_endpoint.destroy()

        # Update storage
        self.node.storage.add_port(inport, self.node.id, inport.owner.id, "in")
        self.node.storage.add_port(outport, self.node.id, outport.owner.id, "out")


    def disconnect(self, callback=None, actor_id=None, port_name=None, port_dir=None, port_id=None):
        """ Do disconnect for port(s)
            callback: an optional callback that gets called with status when finished
            ports identified by only local actor_id:
                actor_id: the actor that all ports will be disconnected on
                callback will be called once when all ports are diconnected or first failed
            local port identified by:
                actor_id, port_name and port_dir='in'/'out' or
                port_id
                callback will be called once when all peer ports (fanout) are disconnected or first failed

            disconnect -*> _disconnect_port -*> _disconnected_port (-*> _disconnecting_actor_cb) -> !
        """
        port_ids = []
        if actor_id and not (port_id or port_name or port_dir):
            # We disconnect all ports on an actor
            try:
                actor = self.node.am.actors[actor_id]
            except:
                # actor not found
                status = response.CalvinResponse(response.NOT_FOUND, "Actor %s must be local" % (actor_id))
                if callback:
                    callback(status=status, actor_id=actor_id, port_name=port_name, port_id=port_id)
                    return
                else:
                    raise Exception(str(status))
            else:
                port_ids.extend([p.id for p in actor.inports.itervalues()])
                port_ids.extend([p.id for p in actor.outports.itervalues()])
                # Need to collect all callbacks into one
                if callback:
                    callback = CalvinCB(self._disconnecting_actor_cb, _callback=callback, port_ids=port_ids)
        else:
            # Just one port to disconnect
            if port_id:
                port_ids.append(port_id)
            else:
                # Awkward but lets get the port id from name etc so that the rest can loop over port ids
                try:
                    port = self._get_local_port(actor_id, port_name, port_dir, port_id)
                except:
                    # not local
                    status = response.CalvinResponse(response.NOT_FOUND, "Port %s on actor %s must be local" % (port_name if port_name else port_id, actor_id if actor_id else "some"))
                    if callback:
                        callback(status=status, actor_id=actor_id, port_name=port_name, port_id=port_id)
                        return
                    else:
                        raise Exception(str(status))
                else:
                    # Found locally
                    port_ids.append(port.id)

        _log.analyze(self.node.id, "+", {'port_ids': port_ids})

        # Run over copy of list of ports since modified inside the loop
        for port_id in port_ids[:]:
            self._disconnect_port(callback, port_id)

    def _disconnect_port(self, callback=None, port_id=None):
        """ Obtain any missing information to enable disconnecting one port and make the disconnect"""
        # Collect all parameters into a state that we keep for the sub functions and callback
        state = {   'callback': callback,
                    'port_id': port_id,
                    'peer_ids': None
                }
        # Check if port actually is local
        try:
            port = self._get_local_port(None, None, None, port_id)
        except:
            # not local
            status = response.CalvinResponse(response.NOT_FOUND, "Port %s must be local" % (port_id))
            if callback:
                callback(status=status, port_id=port_id)
                return
            else:
                raise Exception(str(status))
        else:
            # Found locally
            state['port_name'] = port.name
            state['port_dir'] = "in" if port.direction == "in" else "out"
            state['actor_id'] = port.owner.id if port.owner else None

        port = self.ports[state['port_id']]
        # Now check the peer port, peer_ids is list of (peer_node_id, peer_port_id) tuples
        peer_ids = []
        if port.direction == "in":
            # Inport only have one possible peer
            peer_ids = [port.get_peer()]
        else:
            # Outport have several possible peers
            peer_ids = port.get_peers()

        # Disconnect and destroy the endpoints
        endpoints = port.disconnect()
        for ep in endpoints:
            if isinstance(ep, endpoint.TunnelOutEndpoint):
                self.monitor.unregister_out_endpoint(ep)
            ep.destroy()

        ok = True
        for peer_node_id, peer_port_id in peer_ids:
            if peer_node_id == 'local':
                # Use the disconnect request function since does not matter if local or remote request
                if not self.disconnection_request({'peer_port_id': peer_port_id}):
                    ok = False

        # Inform all the remote ports of the disconnect
        remote_peers = [pp for pp in peer_ids if pp[0] and pp[0] != 'local']
        # Keep track of disconnection of remote peer ports
        self.disconnecting_ports[state['port_id']] = remote_peers
        for peer_node_id, peer_port_id in remote_peers:
            self.proto.port_disconnect(callback=CalvinCB(self._disconnected_port,
                                                         peer_id=(peer_node_id, peer_port_id),
                                                         **state),
                                        port_id=state['port_id'],
                                        peer_node_id=peer_node_id,
                                        peer_port_id=peer_port_id)

        # Done disconnecting the port
        if not remote_peers or not ok:
            self.disconnecting_ports.pop(state['port_id'])
            if state['callback']:
                _log.analyze(self.node.id, "+ DONE", {k: state[k] for k in state.keys() if k != 'callback'})
                state['callback'](status=response.CalvinResponse(ok) , **state)

    def _disconnected_port(self, reply, **state):
        """ Get called for each peer port when diconnecting but callback should only be called once"""
        try:
            # Remove this peer from the list of remote peer ports
            self.disconnecting_ports[state['port_id']].remove(state['peer_id'])
        except:
            pass
        if not reply:
            # Got failed response do callback, but also remove port from dictionary indicating we have sent the callback
            self.disconnecting_ports.pop(state['port_id'])
            if state['callback']:
                state['callback'](status=response.CalvinResponse(False), **state)
        if state['port_id'] in self.disconnecting_ports:
            if not self.disconnecting_ports[state['port_id']]:
                # We still have port in dictionary and now list is empty hence we should send OK
                self.disconnecting_ports.pop(state['port_id'])
                if state['callback']:
                    state['callback'](status=response.CalvinResponse(True), **state)

    def _disconnecting_actor_cb(self, status, _callback, port_ids, **state):
        """ Get called for each of the actor's ports when disconnecting, but callback should only be called once
            status: OK or not
            _callback: original callback
            port_ids: list of port ids kept in context between calls when *changed* by this function, do not replace it
            state: dictionary keeping disconnect information
        """
        # Send negative response if not already done it
        if not status and port_ids:
            if _callback:
                del port_ids[:]
                _callback(status=response.CalvinResponse(False), actor_id=state['actor_id'])
        if state['port_id'] in port_ids:
            # Remove this port from list
            port_ids.remove(state['port_id'])
            # If all ports done send positive response
            if not port_ids:
                if _callback:
                    _callback(status=response.CalvinResponse(True), actor_id=state['actor_id'])

    def disconnection_request(self, payload):
        """ A request from a peer to disconnect a port"""
        if not ('peer_port_id' in payload or
                ('peer_actor_id' in payload and
                'peer_port_name' in payload and
                'peer_port_dir' in payload)):
            # Not enough info to find port
            return response.CalvinResponse(response.BAD_REQUEST)
        # Check if port actually is local
        try:
            port = self._get_local_port(payload['peer_actor_id'] if 'peer_actor_id' in payload else None,
                                        payload['peer_port_name'] if 'peer_port_name' in payload else None,
                                        payload['peer_port_dir'] if 'peer_port_dir' in payload else None,
                                        payload['peer_port_id'] if 'peer_port_id' in payload else None)
        except:
            # We don't have the port
            return response.CalvinResponse(response.NOT_FOUND)
        else:
            # Disconnect and destroy endpoints
            endpoints = port.disconnect()
            for ep in endpoints:
                if isinstance(ep, endpoint.TunnelOutEndpoint):
                    self.monitor.unregister_out_endpoint(ep)
                ep.destroy()

            return response.CalvinResponse(True)

    def add_ports_of_actor(self, actor):
        """ Add an actor's ports to the dictionary, used by actor manager """
        for port in actor.inports.values():
            self.ports[port.id] = port
        for port in actor.outports.values():
            self.ports[port.id] = port

    def remove_ports_of_actor(self, actor):
        """ Remove an actor's ports in the dictionary, used by actor manager """
        for port in actor.inports.values():
            self.ports.pop(port.id)
        for port in actor.outports.values():
            self.ports.pop(port.id)

    def _get_local_port(self, actor_id=None, port_name=None, port_dir=None, port_id=None):
        """ Return a port if it is local otherwise raise exception """
        if port_id and port_id in self.ports:
            return self.ports[port_id]
        if port_name and actor_id and port_dir:
            for port in self.ports.itervalues():
                if port.name == port_name and port.owner and port.owner.id == actor_id and port.direction == port_dir:
                    return port
            # For new shadow actors we create the port
            _log.analyze(self.node.id, "+ SHADOW PORT?", {'actor_id': actor_id, 'port_name': port_name, 'port_dir': port_dir, 'port_id': port_id})
            actor = self.node.am.actors.get(actor_id, None)
            _log.debug("SHADOW ACTOR: %s, %s, %s" % (("SHADOW" if isinstance(actor, ShadowActor) else "NOT SHADOW"), type(actor), actor))
            if isinstance(actor, ShadowActor):
                port = actor.create_shadow_port(port_name, port_dir, port_id)
                _log.analyze(self.node.id, "+ CREATED SHADOW PORT", {'actor_id': actor_id, 'port_name': port_name, 'port_dir': port_dir, 'port_id': port.id if port else None})
                if port:
                    self.ports[port.id] = port
                    return port
        raise Exception("Port '%s' not found locally" % (port_id if port_id else str(actor_id)+"/"+str(port_name)+":"+str(port_dir)))
