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

from calvin.utilities import calvinuuid
from calvin.utilities.utils import enum
from calvin.utilities.calvin_callback import CalvinCB, CalvinCBClass
from calvin.runtime.north.calvin_network import CalvinLink

from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)

class CalvinTunnel(object):
    """CalvinTunnel is a tunnel over the runtime to runtime communication with a peer node"""

    STATUS = enum('PENDING', 'WORKING', 'TERMINATED')

    def __init__(self, links, peer_node_id, tunnel_type, policy, id=None):
        """ links: the calvin networks dictionary of links
            peer_node_id: the id of the peer that we use
            tunnel_type: what is the usage of the tunnel
            policy: TODO not used currently
            id: Tunnel objects on both nodes will use the same id number hence only supply if provided from other side
        """
        super(CalvinTunnel, self).__init__()
        # The tunnel only use one link (links[peer_node_id]) at a time but it can switch at any point
        self.links = links
        self.peer_node_id = peer_node_id
        self.tunnel_type = tunnel_type
        self.policy = policy
        # id may change while status is PENDING, but is fixed in WORKING
        self.id = id if id else calvinuuid.uuid("TUNNEL")
        # If id supplied then we must be the second end and hence working
        self.status = CalvinTunnel.STATUS.WORKING if id else CalvinTunnel.STATUS.PENDING
        # Add the tunnel to the current link (will be migrated for us if switch link)
        if self.peer_node_id in self.links:
            self.links[self.peer_node_id].tunnels[self.id] = self
        # The callbacks recv for incoming message, down for tunnel failed or died, up for tunnel working 
        self.recv_handler = None
        self.down_handler = None
        self.up_handler = None

    def _late_link(self, peer_node_id):
        """ Sometimes the peer is unknown even when a tunnel object is needed.
             This method is called when we have the peer node id.
        """
        self.peer_node_id = peer_node_id
        if self.peer_node_id in self.links:
            self.links[self.peer_node_id].tunnels[self.id] = self

    def _update_id(self, id):
        """ While status PENDING we might have a simulataneous tunnel setup
            from both sides. The tunnel with highest id is used, this is
            solved by changing the id for the existing tunnel object with
            this method instead of creating a new and destroying the other.
        """
        old_id = self.id
        self.id = id
        self.links[self.peer_node_id].tunnels.pop(old_id)
        self.links[self.peer_node_id].tunnels[self.id] = self

    def _setup_ack(self, reply):
        """ Gets called when the tunnel request is acknowledged by the other side """
        if reply['tunnel_id'] != self.id:
            self._update_id(reply['tunnel_id'])
        if reply['status'] == 'ACK':
            self.status = CalvinTunnel.STATUS.WORKING
            if self.up_handler:
                self.up_handler()
        else:
            self.status = CalvinTunnel.STATUS.TERMINATED
            if self.down_handler:
                self.down_handler()

    def _destroy_ack(self, reply):
        """ Gets called when the tunnel destruction is acknowledged by the other side """
        self.close(local_only=True)
        if reply != 'ACK':
            raise Exception("Got none ack on destruction of tunnel!\n%s" % reply)

    def send(self, payload):
        """ Send a payload over the tunnel 
            payload must be serializable, i.e. only built-in types such as:
            dict, list, tuple, string, numbers, booleans, etc
        """
        msg = {'cmd': 'TUNNEL_DATA', 'value': payload, 'tunnel_id': self.id}
        self.links[self.peer_node_id].send(msg)

    def register_recv(self, handler):
        """ Register the handler of incoming messages on this tunnel """
        self.recv_handler = handler

    def register_tunnel_down(self, handler):
        """ Register the handler of tunnel down"""
        self.down_handler = handler

    def register_tunnel_up(self, handler):
        """ Register the handler of tunnel up"""
        self.up_handler = handler

    def close(self, local_only=False):
        """ Removes the tunnel but does not inform
            other end when local_only.
            
            Currently does not support local_only == False
        """
        self.status = CalvinTunnel.STATUS.TERMINATED
        self.links[self.peer_node_id].tunnels.pop(self.id)
        if not local_only:
            #FIXME use the tunnel_destroy cmd directly instead
            raise NotImplementedError()

class CalvinProto(CalvinCBClass):
    """ CalvinProto class is the interface between runtimes for all runtime
        subsystem that need to interact. It uses the links in network.
        
        Besides handling tunnel setup etc, it mainly formats commands uniformerly.
    """

    def __init__(self, node, network, tunnel_handlers=None):
        super(CalvinProto, self).__init__({
            # The commands in messages is called using the CalvinCBClass.
            # Hence it is possible for others to register additional
            # functions that should be called. Either permanent here
            # or using the callback_register method.
            'ACTOR_NEW': [CalvinCB(self.actor_new_handler)],
            'ACTOR_DESTROY': [CalvinCB(self.actor_destroy_handler)],
            'PORT_CONNECT': [CalvinCB(self.port_connect_handler)],
            'PORT_DISCONNECT': [CalvinCB(self.port_disconnect_handler)],
            'PORT_PENDING_MIGRATE': [CalvinCB(self.not_impl_handler)],
            'PORT_COMMIT_MIGRATE': [CalvinCB(self.not_impl_handler)],
            'PORT_CANCEL_MIGRATE': [CalvinCB(self.not_impl_handler)],
            'TUNNEL_NEW': [CalvinCB(self.tunnel_new_handler)],
            'TUNNEL_DESTROY': [CalvinCB(self.tunnel_destroy_handler)],
            'TUNNEL_DATA': [CalvinCB(self.tunnel_data_handler)],
            'STORE_GET': [CalvinCB(self.not_impl_handler)],
            'STORE_PUT': [CalvinCB(self.not_impl_handler)],
            'STORE_SET_APPEND': [CalvinCB(self.not_impl_handler)],
            'STORE_SET_REMOVE': [CalvinCB(self.not_impl_handler)],
            'STORE_DELETE': [CalvinCB(self.not_impl_handler)],
            'REPLY': [CalvinCB(self.reply_handler)]})

        self.rt_id = node.id
        self.node = node
        self.network = network
        # Register the function that receives all incoming messages
        self.network.register_recv(CalvinCB(self.recv_handler))
        # tunnel_handlers is a dict with key: tunnel_type string e.g. 'token', value: function that get request
        self.tunnel_handlers = tunnel_handlers if isinstance(tunnel_handlers, dict) else {}

    #
    # Reception of incoming payload
    #

    def not_impl_handler(self, payload):
        raise NotImplementedError()

    def reply_handler(self, payload):
        """ Map to specified link's reply_handler"""
        self.network.links[payload['from_rt_uuid']].reply_handler(payload)

    def recv_handler(self, tp_link, payload):
        """ Called by transport when a full payload has been received
        """
        try:
            self.network.link_check(payload['from_rt_uuid'])
        except:
            raise Exception("ERROR_UNKNOWN_RUNTIME")

        if not ('cmd' in payload and payload['cmd'] in self.callback_valid_names()):
            raise Exception("ERROR_UNKOWN_COMMAND")
        # Call the proper handler for the command using CalvinCBClass
        self._callback_execute(payload['cmd'], payload)

    #
    # Remote commands supported by protocol
    #

    #### ACTORS ####

    def actor_new(self, to_rt_uuid, callback, actor_type, state, prev_connections):
        """ Creates a new actor on to_rt_uuid node, but is only intended for migrating actors 
            callback: called when finished with the peers respons as argument
            actor_type: see actor manager
            state: see actor manager
            prev_connections: see actor manager
        """
        if self.network.link_request(to_rt_uuid):
            # Already have link just continue in _actor_new
            self._actor_new(to_rt_uuid, callback, actor_type, state, prev_connections)
        else:
            # Request link before continue in _actor_new
            self.node.network.link_request(to_rt_uuid, CalvinCB(self._actor_new,
                                                        to_rt_uuid=to_rt_uuid,
                                                        callback=callback,
                                                        actor_type=actor_type,
                                                        state=state,
                                                        prev_connections=prev_connections))

    def _actor_new(self, to_rt_uuid, callback, actor_type, state, prev_connections, status='ACK', uri=None):
        """ Got link? continue actor new """
        if status=='ACK':
            msg = {'cmd': 'ACTOR_NEW',
                   'state':{'actor_type': actor_type, 'actor_state': state, 'prev_connections':prev_connections}}
            self.network.links[to_rt_uuid].send_with_reply(callback, msg)
        else:
            callback(status=status)

    def actor_new_handler(self, payload):
        """ Peer request new actor with state and connections """
        self.node.am.new(payload['state']['actor_type'],
                         None,
                         payload['state']['actor_state'],
                         payload['state']['prev_connections'],
                         callback=CalvinCB(self._actor_new_handler, payload))

    def _actor_new_handler(self, payload, status, **kwargs):
        """ Potentially created actor, reply to requesting node """
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': status}
        self.network.links[payload['from_rt_uuid']].send(msg)

    def actor_destroy(self, to_rt_uuid, callback, actor_id):
        """ Destroys a remote actor on to_rt_uuid node
            callback: called when finished with the peers respons as argument
            actor_id: the actor to destroy
            
            TODO: should we allow remote destruction?
        """
        try:
            self.network.link_check(to_rt_uuid)
        except:
            raise Exception("ERROR_UNKNOWN_RUNTIME")
        msg = {'cmd': 'ACTOR_DESTROY', 'actor_uuid': actor_id}
        self.network.links[to_rt_uuid].send_with_reply(callback, msg)

    def actor_destroy_handler(self, payload):
        """ Peer request destruction of actor """
        reply = "ACK"
        try:
            self.node.am.destroy(payload['actor_uuid'])
        except:
            reply = "NACK"
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply}
        self.network.links[payload['from_rt_uuid']].send(msg)

    #### TUNNELS ####

    def register_tunnel_handler(self, tunnel_type, handler):
        """ Any users of tunnels need to register a handler for a tunnel_type.
            The handler will be called when a peer request a tunnel.
            tunnel_type: string specify the tunnel usage, e.g. 'token'
            handler: function that takes tunnel as argument and returns True if it accepts and False otherwise
        """
        self.tunnel_handlers[tunnel_type] = handler

    def tunnel_new(self, to_rt_uuid, tunnel_type, policy):
        """ Either create a new tunnel (request side), with status pending,
            or return an existing tunnel with the same tunnel_type
            to_rt_uuid: peer node id
            tunnel_type: tunnel usage string
            policy: Not currently used
        """
        try:
            self.network.link_check(to_rt_uuid)
        except:
            # Need to join the other peer first
            # Create a tunnel object which is not inserted on a link yet
            tunnel = CalvinTunnel(self.network.links, None, tunnel_type, policy)
            _log.debug("Request for tunnel on rt to rt (%s) link that is not yet established" % (to_rt_uuid))
            self.network.link_request(to_rt_uuid, CalvinCB(self._tunnel_link_request_finished, tunnel=tunnel, to_rt_uuid=to_rt_uuid, tunnel_type=tunnel_type, policy=policy))
            return tunnel
        
        # Do we have a tunnel already?
        tunnel = self.network.links[to_rt_uuid].get_tunnel(tunnel_type = tunnel_type)
        if tunnel != None:
            return tunnel

        # Create new tunnel and send request to peer
        tunnel = CalvinTunnel(self.network.links, to_rt_uuid, tunnel_type, policy)
        self._tunnel_new_msg(tunnel, to_rt_uuid, tunnel_type, policy)
        return tunnel

    def _tunnel_new_msg(self, tunnel, to_rt_uuid, tunnel_type, policy):
        """ Create and send the tunnel new message """
        msg = {'cmd': 'TUNNEL_NEW', 'type': tunnel_type, 'tunnel_id': tunnel.id, 'policy': policy}
        self.network.links[to_rt_uuid].send_with_reply(CalvinCB(tunnel._setup_ack), msg)

    def _tunnel_link_request_finished(self, status, tunnel, to_rt_uuid, tunnel_type, policy, uri=None):
        """ Got a link, now continue with tunnel setup """
        _log.debug("Request (by a tunnel) for rt to rt (%s) link is established" % (to_rt_uuid))
        try:
            self.network.link_check(to_rt_uuid)
        except:
            # For some reason we still did not have a link
            if isinstance(status, Exception):
                raise status
            else:
                raise Exception("ERROR_UNKNOWN_RUNTIME")

        # Set the link and send request for new tunnel
        tunnel._late_link(to_rt_uuid)
        self._tunnel_new_msg(tunnel, to_rt_uuid, tunnel_type, policy)
        return None

    def tunnel_new_handler(self, payload):
        """ Create a new tunnel (response side) """
        link = self.network.links[payload['from_rt_uuid']]
        tunnel = link.get_tunnel(payload['type'])
        ok = False
        if tunnel:
            _log.debug("GOT TUNNEL NEW request while we already have one pending")
            # Got tunnel new request while we already have one pending
            # it is not allowed to send new request while a tunnel is working
            if tunnel.status != CalvinTunnel.STATUS.WORKING:
                ok = True
                # The one with lowest tunnel id loose
                if tunnel.id < payload['tunnel_id']:
                    # Our tunnel has lowest id, change our tunnels id
                    # update status and call proper callbacks
                    tunnel._setup_ack({'status': 'ACK', 'tunnel_id': payload['tunnel_id']})
        else:
            # No simultaneous tunnel requests, lets create it...
            tunnel = CalvinTunnel(self.network.links, payload['from_rt_uuid'], payload['type'], payload['policy'], payload['tunnel_id'])
            try:
                # ... and see if the handler wants it
                ok = self.tunnel_handlers[payload['type']](tunnel)
            except:
                pass
        # Send the response
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': {'status':'ACK' if ok else 'NACK', 'tunnel_id': tunnel.id}}
        self.network.links[payload['from_rt_uuid']].send(msg)

        # If handler did not want it close it again
        if not ok:
            tunnel.close(local_only=True)

    def tunnel_destroy(self, to_rt_uuid, tunnel_uuid):
        """ Destroy a tunnel (request side) """
        try:
            self.network.link_check(to_rt_uuid)
        except:
            raise Exception("ERROR_UNKNOWN_RUNTIME")
        try:
            tunnel = self.network.links[to_rt_uuid].tunnels[tunnel_uuid]
        except:
            raise Exception("ERROR_UNKNOWN_TUNNEL")
        # It exist, lets request its destruction
        msg = {'cmd': 'TUNNEL_DESTROY', 'tunnel_id': tunnel.id}
        self.network.links[to_rt_uuid].send_with_reply(CalvinCB(tunnel._destroy_ack), msg)

    def tunnel_destroy_handler(self, payload):
        """ Destroy tunnel (response side) """
        try:
            tunnel = self.network.links[payload['from_rt_uuid']].tunnels[payload['tunnel_id']]
        except:
            raise Exception("ERROR_UNKNOWN_TUNNEL")
        # We have the tunnel so close it
        tunnel.close(local_only=True)
        ok = False
        try:
            # Hope the tunnel don't mind,
            # TODO since the requester likely don't know what to do and we have already closed it
            ok = tunnel.down_handler()
        except:
            pass
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': 'ACK' if ok else 'NACK'}
        self.network.links[payload['from_rt_uuid']].send(msg)

    def tunnel_data_handler(self, payload):
        """ Map received data over tunnel to the correct link and tunnel """
        try:
            self.network.links[payload['from_rt_uuid']].tunnels[payload['tunnel_id']].recv_handler(payload['value'])
        except:
            raise Exception("ERROR_UNKNOWN_TUNNEL")

    #### PORTS ####

    def port_connect(self, callback=None, port_id=None, peer_node_id=None, peer_port_id=None, peer_actor_id=None, peer_port_name=None, peer_port_dir=None, tunnel=None):
        """ Before calling this method all needed information and when requested a tunnel must be available
            see port manager for parameters
        """
        if tunnel:
            msg = {'cmd': 'PORT_CONNECT', 'port_id': port_id, 'peer_actor_id': peer_actor_id, 'peer_port_name': peer_port_name, 'peer_port_id': peer_port_id, 'peer_port_dir': peer_port_dir, 'tunnel_id':tunnel.id}
            self.network.links[peer_node_id].send_with_reply(callback, msg)
        else:
            raise NotImplementedError()

    def port_connect_handler(self, payload):
        """ Request for port connection """
        reply = self.node.pm.connection_request(payload)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply}
        self.network.links[payload['from_rt_uuid']].send(msg)

    def port_disconnect(self, callback=None, port_id=None, peer_node_id=None, peer_port_id=None, peer_actor_id=None, peer_port_name=None, peer_port_dir=None, tunnel=None):
        """ Before calling this method all needed information must be available
            see port manager for parameters
        """
        msg = {'cmd': 'PORT_DISCONNECT', 'port_id': port_id, 'peer_actor_id': peer_actor_id, 'peer_port_name': peer_port_name, 'peer_port_id': peer_port_id, 'peer_port_dir': peer_port_dir}
        self.network.links[peer_node_id].send_with_reply(callback, msg)

    def port_disconnect_handler(self, payload):
        """ Reguest for port disconnect """
        reply = self.node.pm.disconnection_request(payload)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply}
        self.network.links[payload['from_rt_uuid']].send(msg)

if __name__ == '__main__':
    import pytest
    pytest.main("-vs runtime/north/tests/test_calvin_proto.py")
