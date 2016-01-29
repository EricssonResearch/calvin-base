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
from calvin.actor.actorport import InPort, OutPort
from calvin.runtime.south import endpoint
from calvin.runtime.north.calvin_proto import CalvinTunnel
import calvin.requests.calvinresponse as response
from calvin.utilities import calvinlogger
from calvin.actor.actor import ShadowActor

_log = calvinlogger.get_logger(__name__)


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

            if isinstance(port, InPort):
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
            if isinstance(port, InPort):
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
                    \> _connect_by_peer_port_id /           \-> _connect_via_local -!
                    \-> _connect_by_actor_id ---/
        """
        # Collect all parameters into a state that we keep between the chain of callbacks needed to complete a connection
        state = {   'callback': callback,
                    'actor_id': actor_id,
                    'port_name': port_name,
                    'port_dir': port_dir,
                    'port_id': port_id,
                    'peer_node_id': peer_node_id,
                    'peer_actor_id': peer_actor_id,
                    'peer_port_name': peer_port_name,
                    'peer_port_dir': peer_port_dir,
                    'peer_port_id': peer_port_id
                }
        _log.analyze(self.node.id, "+", {k: state[k] for k in state.keys() if k != 'callback'},
                    peer_node_id=state['peer_node_id'], tb=True)
        try:
            port = self._get_local_port(actor_id, port_name, port_dir, port_id)
        except:
            # not local
            if port_id:
                status = response.CalvinResponse(response.BAD_REQUEST, "First port %s must be local" % (port_id))
            else:
                status = response.CalvinResponse(response.BAD_REQUEST, "First port %s on actor %s must be local" % (port_name, actor_id))
            if callback:
                callback(status=status,
                         actor_id=actor_id,
                         port_name=port_name,
                         port_id=port_id,
                         peer_node_id=peer_node_id,
                         peer_actor_id=peer_actor_id,
                         peer_port_name=peer_port_name,
                         peer_port_id=peer_port_id)
                return
            else:
                raise Exception(str(status))
        else:
            # Found locally
            state['port_id'] = port.id

        # Check if the peer port is local even if a missing peer_node_id
        if not peer_node_id and peer_actor_id in self.node.am.actors.iterkeys():
            state['peer_node_id'] = self.node.id

        if not state['peer_node_id'] and state['peer_port_id']:
            try:
                self._get_local_port(None, None, None, peer_port_id)
            except:
                # not local
                pass
            else:
                # Found locally
                state['peer_node_id'] = self.node.id

        # Still no peer node id? ...
        if not state['peer_node_id']:
            if state['peer_port_id']:
                # ... but an id of a port lets ask for more info
                self.node.storage.get_port(state['peer_port_id'], CalvinCB(self._connect_by_peer_port_id, **state))
                return
            elif state['peer_actor_id'] and state['peer_port_name']:
                # ... but an id of an actor lets ask for more info
                self.node.storage.get_actor(state['peer_actor_id'], CalvinCB(self._connect_by_peer_actor_id, **state))
                return
            else:
                # ... and no info on how to get more info, abort
                status=response.CalvinResponse(response.BAD_REQUEST, "Need peer_node_id (%s), peer_actor_id(%s) and/or peer_port_id(%s)" % (peer_node_id, peer_actor_id, peer_port_id))
                if callback:
                    callback(status=status, actor_id=actor_id, port_name=port_name, port_id=port_id, peer_node_id=peer_node_id, peer_actor_id=peer_actor_id, peer_port_name=peer_port_name, peer_port_id=peer_port_id)
                    return
                else:
                    raise Exception(str(status))
        else:
            if not ((peer_actor_id and peer_port_name) or peer_port_id):
                # We miss information on to find the peer port
                status=response.CalvinResponse(response.BAD_REQUEST, "Need peer_port_name (%s), peer_actor_id(%s) and/or peer_port_id(%s)" % (peer_port_name, peer_actor_id, peer_port_id))
                if callback:
                    callback(status=status, actor_id=actor_id, port_name=port_name, port_id=port_id, peer_node_id=peer_node_id, peer_actor_id=peer_actor_id, peer_port_name=peer_port_name, peer_port_id=peer_port_id)
                    return
                else:
                    raise Exception(str(status))

        self._connect(**state)

    def _connect_by_peer_port_id(self, key, value, **state):
        """ Gets called when storage responds with peer port information """
        _log.analyze(self.node.id, "+", {k: state[k] for k in state.keys() if k != 'callback'},
                     peer_node_id=state['peer_node_id'], tb=True)
        if not isinstance(value, dict):
            if state['callback']:
                state['callback'](status=response.CalvinResponse(response.BAD_REQUEST, "Storage return invalid information"), **state)
                return
            else:
                raise Exception("Storage return invalid information")

        if not state['peer_node_id'] and 'node_id' in value and value['node_id']:
            state['peer_node_id'] = value['node_id']
        else:
            if state['callback']:
                state['callback'](status=response.CalvinResponse(response.BAD_REQUEST, "Storage return invalid information"), **state)
                return
            else:
                raise Exception("Storage return invalid information")

        self._connect(**state)

    def _connect_by_peer_actor_id(self, key, value, **state):
        """ Gets called when storage responds with peer actor information"""
        _log.analyze(self.node.id, "+", {k: state[k] for k in state.keys() if k != 'callback'},
                        peer_node_id=state['peer_node_id'], tb=True)
        if not isinstance(value, dict):
            if state['callback']:
                state['callback'](status=response.CalvinResponse(response.BAD_REQUEST, "Storage return invalid information"), **state)
                return
            else:
                raise Exception("Storage return invalid information")

        if not state['peer_node_id'] and 'node_id' in value and value['node_id']:
            state['peer_node_id'] = value['node_id']
        else:
            if state['callback']:
                state['callback'](status=response.CalvinResponse(response.BAD_REQUEST, "Storage return invalid information"), **state)
                return
            else:
                raise Exception("Storage return invalid information")

        self._connect(**state)

    def _connect(self, **state):
        """ Do the connection of ports, all neccessary information supplied but
            maybe not all pre-requisites for remote connections.
        """
        _log.analyze(self.node.id, "+", {k: state[k] for k in state.keys() if k != 'callback'},
                        peer_node_id=state['peer_node_id'], tb=True)
        # Local connect
        if self.node.id == state['peer_node_id']:
            _log.analyze(self.node.id, "+ LOCAL", {k: state[k] for k in state.keys() if k != 'callback'}, peer_node_id=state['peer_node_id'])
            port1 = self._get_local_port(state['actor_id'], state['port_name'], state['port_dir'], state['port_id'])
            port2 = self._get_local_port(state['peer_actor_id'], state['peer_port_name'], state['peer_port_dir'], state['peer_port_id'])
            # Local connect wants the first port to be an inport
            inport , outport = (port1, port2) if isinstance(port1, InPort) else (port2, port1)
            self._connect_via_local(inport, outport)
            if state['callback']:
                state['callback'](status=response.CalvinResponse(True) , **state)
            return None

        # Remote connection
        # TODO Currently we only have support for setting up a remote connection via tunnel
        tunnel = None
        if not state['peer_node_id'] in self.tunnels.iterkeys():
            # No tunnel to peer, get one first
            _log.analyze(self.node.id, "+ GET TUNNEL", {k: state[k] for k in state.keys() if k != 'callback'}, peer_node_id=state['peer_node_id'])
            tunnel = self.proto.tunnel_new(state['peer_node_id'], 'token', {})
            tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
            tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
            tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
            self.tunnels[state['peer_node_id']] = tunnel
        else:
            tunnel = self.tunnels[state['peer_node_id']]

        if tunnel.status == CalvinTunnel.STATUS.PENDING:
            if not state['peer_node_id'] in self.pending_tunnels:
                self.pending_tunnels[state['peer_node_id']] = []
            # call _connect_via_tunnel when we get the response of the tunnel
            self.pending_tunnels[state['peer_node_id']].append(CalvinCB(self._connect_via_tunnel, **state))
            return
        elif tunnel.status == CalvinTunnel.STATUS.TERMINATED:
            # TODO should we retry at this level?
            if state['callback']:
                state['callback'](status=response.CalvinResponse(response.INTERNAL_ERROR), **state)
            return

        _log.analyze(self.node.id, "+ HAD TUNNEL", dict({k: state[k] for k in state.keys() if k != 'callback'},tunnel_status=self.tunnels[state['peer_node_id']].status), peer_node_id=state['peer_node_id'])
        self._connect_via_tunnel(status=response.CalvinResponse(True), **state)

    def _connect_via_tunnel(self, status=None, **state):
        """ All information and hopefully (status OK) a tunnel to the peer is available for a port connect"""
        port = self._get_local_port(state['actor_id'], state['port_name'], state['port_dir'], state['port_id'])
        _log.analyze(self.node.id, "+ " + str(status),
                     dict({k: state[k] for k in state.keys() if k != 'callback'},port_is_connected=port.is_connected_to(state['peer_port_id'])),
                     peer_node_id=state['peer_node_id'], tb=True)
        if port.is_connected_to(state['peer_port_id']):
            # The other end beat us to connecting the port, lets just report success and return
            _log.analyze(self.node.id, "+ IS CONNECTED", {k: state[k] for k in state.keys() if k != 'callback'}, peer_node_id=state['peer_node_id'])
            if state['callback']:
                state['callback'](status=response.CalvinResponse(True), **state)
            return None

        if not status:
            # Failed getting a tunnel, just inform the one wanting to connect
            if state['callback']:
                state['callback'](status=response.CalvinResponse(response.INTERNAL_ERROR), **state)
                return None
        # Finally we have all information and a tunnel
        # Lets ask the peer if it can connect our port.
        tunnel = self.tunnels[state['peer_node_id']]
        _log.analyze(self.node.id, "+ SENDING", dict({k: state[k] for k in state.keys() if k != 'callback'},tunnel_status=self.tunnels[state['peer_node_id']].status), peer_node_id=state['peer_node_id'])
        if 'retries' not in state:
            state['retries'] = 0
        self.proto.port_connect(callback=CalvinCB(self._connected_via_tunnel, **state),
                                port_id=state['port_id'],
                                peer_node_id=state['peer_node_id'],
                                peer_port_id=state['peer_port_id'],
                                peer_actor_id=state['peer_actor_id'],
                                peer_port_name=state['peer_port_name'],
                                peer_port_dir=state['peer_port_dir'], tunnel=tunnel)


    def _connected_via_tunnel(self, reply, **state):
        """ Gets called when remote responds to our request for port connection """
        _log.analyze(self.node.id, "+ " + str(reply), {k: state[k] for k in state.keys() if k != 'callback'},
                    peer_node_id=state['peer_node_id'], tb=True)
        if reply in [response.BAD_REQUEST, response.NOT_FOUND, response.GATEWAY_TIMEOUT]:
            # Other end did not accept our port connection request
            if state['retries'] < 2 and state['peer_node_id']:
                # Maybe it is on another node now lets retry and lookup the port
                state['peer_node_id'] = None
                state['retries'] += 1
                self.node.storage.get_port(state['peer_port_id'], CalvinCB(self._connect_by_peer_port_id, **state))
                return None
            if state['callback']:
                state['callback'](status=response.CalvinResponse(response.NOT_FOUND), **state)
                return None

        if reply == response.GONE:
            # Other end did not accept our port connection request, likely due to they have not got the message
            # about the tunnel in time
            _log.analyze(self.node.id, "+ RETRY", {k: state[k] for k in state.keys() if k != 'callback'}, peer_node_id=state['peer_node_id'])
            if state['retries']<3:
                state['retries'] += 1
                # Status here just indicate that we should have a tunnel
                self._connect_via_tunnel(status=response.CalvinResponse(True), **state)
                return None
            else:
                if state['callback']:
                    state['callback'](status=response.CalvinResponse(False), **state)
                return None

        # Set up the port's endpoint
        tunnel = self.tunnels[state['peer_node_id']]
        port = self.ports[state['port_id']]
        if isinstance(port, InPort):
            endp = endpoint.TunnelInEndpoint(port,
                                             tunnel,
                                             state['peer_node_id'],
                                             reply.data['port_id'],
                                             self.node.sched.trigger_loop)
        else:
            endp = endpoint.TunnelOutEndpoint(port,
                                              tunnel,
                                              state['peer_node_id'],
                                              reply.data['port_id'],
                                              self.node.sched.trigger_loop)
            # register into main loop
            self.monitor.register_out_endpoint(endp)
        invalid_endpoint = port.attach_endpoint(endp)
        # remove previous endpoint
        if invalid_endpoint:
            if isinstance(invalid_endpoint, endpoint.TunnelOutEndpoint):
                self.monitor.unregister_out_endpoint(invalid_endpoint)
            invalid_endpoint.destroy()

        # Done connecting the port
        if state['callback']:
            state['callback'](status=response.CalvinResponse(True), **state)

        # Update storage
        if isinstance(port, InPort):
            self.node.storage.add_port(port, self.node.id, port.owner.id, "in")
        else:
            self.node.storage.add_port(port, self.node.id, port.owner.id, "out")


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
            state['port_dir'] = "in" if isinstance(port, InPort) else "out"
            state['actor_id'] = port.owner.id if port.owner else None

        port = self.ports[state['port_id']]
        # Now check the peer port, peer_ids is list of (peer_node_id, peer_port_id) tuples
        peer_ids = []
        if isinstance(port, InPort):
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
                if port.name == port_name and port.owner and port.owner.id == actor_id and isinstance(port, InPort if port_dir == "in" else OutPort):
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
