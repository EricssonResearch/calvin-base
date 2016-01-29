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
from calvin.utilities import calvinlogger
import calvin.requests.calvinresponse as response

_log = calvinlogger.get_logger(__name__)


class CalvinTunnel(object):
    """CalvinTunnel is a tunnel over the runtime to runtime communication with a peer node"""

    STATUS = enum('PENDING', 'WORKING', 'TERMINATED')

    def __init__(self, links, tunnels, peer_node_id, tunnel_type, policy, rt_id=None, id=None):
        """ links: the calvin networks dictionary of links
            peer_node_id: the id of the peer that we use
            tunnel_type: what is the usage of the tunnel
            policy: TODO not used currently
            id: Tunnel objects on both nodes will use the same id number hence only supply if provided from other side
        """
        super(CalvinTunnel, self).__init__()
        # The tunnel only use one link (links[peer_node_id]) at a time but it can switch at any point
        self.links = links
        self.tunnels = tunnels
        self.peer_node_id = peer_node_id
        self.tunnel_type = tunnel_type
        self.policy = policy
        self.rt_id = rt_id
        # id may change while status is PENDING, but is fixed in WORKING
        self.id = id if id else calvinuuid.uuid("TUNNEL")
        # If id supplied then we must be the second end and hence working
        self.status = CalvinTunnel.STATUS.WORKING if id else CalvinTunnel.STATUS.PENDING
        # Add the tunnel to the dictionary
        if self.peer_node_id:
            if self.peer_node_id in self.tunnels:
                self.tunnels[self.peer_node_id][self.id]=self
            else:
                self.tunnels[self.peer_node_id] = {self.id: self}
        # The callbacks recv for incoming message, down for tunnel failed or died, up for tunnel working
        self.recv_handler = None
        self.down_handler = None
        self.up_handler = None

    def _late_link(self, peer_node_id):
        """ Sometimes the peer is unknown even when a tunnel object is needed.
             This method is called when we have the peer node id.
        """
        self.peer_node_id = peer_node_id
        if self.peer_node_id:
            if self.peer_node_id in self.tunnels:
                self.tunnels[self.peer_node_id][self.id]=self
            else:
                self.tunnels[self.peer_node_id] = {self.id: self}

    def _update_id(self, id):
        """ While status PENDING we might have a simulataneous tunnel setup
            from both sides. The tunnel with highest id is used, this is
            solved by changing the id for the existing tunnel object with
            this method instead of creating a new and destroying the other.
        """
        old_id = self.id
        self.id = id
        self.tunnels[self.peer_node_id].pop(old_id)
        self.tunnels[self.peer_node_id][self.id]=self

    def _setup_ack(self, reply):
        """ Gets called when the tunnel request is acknowledged by the other side """
        if reply and reply.data['tunnel_id'] != self.id:
            self._update_id(reply.data['tunnel_id'])
        if reply:
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
        if not reply:
            _log.error("Got none ack on destruction of tunnel!\n%s" % reply)

    def send(self, payload):
        """ Send a payload over the tunnel
            payload must be serializable, i.e. only built-in types such as:
            dict, list, tuple, string, numbers, booleans, etc
        """
        msg = {'cmd': 'TUNNEL_DATA', 'value': payload, 'tunnel_id': self.id}
        try:
            self.links[self.peer_node_id].send(msg)
        except:
            # FIXME we failed sending should resend after establishing the link if our node is not quiting
            # so far only seen during node quit
            _log.analyze(self.rt_id, "+ TUNNEL FAILED", payload, peer_node_id=self.peer_node_id)

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
        self.tunnels[self.peer_node_id].pop(self.id)
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
            'ACTOR_MIGRATE': [CalvinCB(self.actor_migrate_handler)],
            'APP_DESTROY': [CalvinCB(self.app_destroy_handler)],
            'PORT_CONNECT': [CalvinCB(self.port_connect_handler)],
            'PORT_DISCONNECT': [CalvinCB(self.port_disconnect_handler)],
            'PORT_PENDING_MIGRATE': [CalvinCB(self.not_impl_handler)],
            'PORT_COMMIT_MIGRATE': [CalvinCB(self.not_impl_handler)],
            'PORT_CANCEL_MIGRATE': [CalvinCB(self.not_impl_handler)],
            'TUNNEL_NEW': [CalvinCB(self.tunnel_new_handler)],
            'TUNNEL_DESTROY': [CalvinCB(self.tunnel_destroy_handler)],
            'TUNNEL_DATA': [CalvinCB(self.tunnel_data_handler)],
            'REPLY': [CalvinCB(self.reply_handler)]})

        self.rt_id = node.id
        self.node = node
        self.network = network
        # Register the function that receives all incoming messages
        self.network.register_recv(CalvinCB(self.recv_handler))
        # tunnel_handlers is a dict with key: tunnel_type string e.g. 'token', value: function that get request
        self.tunnel_handlers = tunnel_handlers if isinstance(tunnel_handlers, dict) else {}
        self.tunnels = {}  # key: peer node id, value: dict with key: tunnel_id, value: tunnel obj

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
        _log.analyze(self.rt_id, "RECV", payload)
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
        if self.node.network.link_request(to_rt_uuid, CalvinCB(self._actor_new,
                                                        to_rt_uuid=to_rt_uuid,
                                                        callback=callback,
                                                        actor_type=actor_type,
                                                        state=state,
                                                        prev_connections=prev_connections)):
            # Already have link just continue in _actor_new
                self._actor_new(to_rt_uuid, callback, actor_type, state, prev_connections, status=response.CalvinResponse(True))

    def _actor_new(self, to_rt_uuid, callback, actor_type, state, prev_connections, status, peer_node_id=None, uri=None):
        """ Got link? continue actor new """
        if status:
            msg = {'cmd': 'ACTOR_NEW',
                   'state':{'actor_type': actor_type, 'actor_state': state, 'prev_connections':prev_connections}}
            self.network.links[to_rt_uuid].send_with_reply(callback, msg)
        elif callback:
            callback(status=status)

    def actor_new_handler(self, payload):
        """ Peer request new actor with state and connections """
        _log.analyze(self.rt_id, "+", payload, tb=True)
        self.node.am.new(payload['state']['actor_type'],
                         None,
                         payload['state']['actor_state'],
                         payload['state']['prev_connections'],
                         callback=CalvinCB(self._actor_new_handler, payload))

    def _actor_new_handler(self, payload, status, **kwargs):
        """ Potentially created actor, reply to requesting node """
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': status.encode()}
        self.network.links[payload['from_rt_uuid']].send(msg)

    def actor_migrate(self, to_rt_uuid, callback, actor_id, requirements, extend=False, move=False):
        """ Request actor on to_rt_uuid node to migrate accoring to new deployment requirements
            callback: called when finished with the status respons as argument
            actor_id: actor_id to migrate
            requirements: see app manager
            extend: if extending current deployment requirements
            move: if prefers to move from node
        """
        if self.node.network.link_request(to_rt_uuid, CalvinCB(self._actor_migrate,
                                                        to_rt_uuid=to_rt_uuid,
                                                        callback=callback,
                                                        actor_id=actor_id,
                                                        requirements=requirements,
                                                        extend=extend,
                                                        move=move)):
            # Already have link just continue in _actor_new
                self._actor_migrate(to_rt_uuid, callback, actor_id, requirements,
                                    extend, move, status=response.CalvinResponse(True))

    def _actor_migrate(self, to_rt_uuid, callback, actor_id, requirements, extend, move, status,
                       peer_node_id=None, uri=None):
        """ Got link? continue actor migrate """
        if status:
            msg = {'cmd': 'ACTOR_MIGRATE',
                   'requirements': requirements, 'actor_id': actor_id, 'extend': extend, 'move': move}
            self.network.links[to_rt_uuid].send_with_reply(callback, msg)
        elif callback:
            callback(status=status)

    def actor_migrate_handler(self, payload):
        """ Peer request new actor with state and connections """
        self.node.am.update_requirements(payload['actor_id'], payload['requirements'],
                                         payload['extend'], payload['move'],
                                         callback=CalvinCB(self._actor_migrate_handler, payload))

    def _actor_migrate_handler(self, payload, status, **kwargs):
        """ Potentially migrated actor, reply to requesting node """
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': status.encode()}
        self.network.links[payload['from_rt_uuid']].send(msg)

    #### APPS ####

    def app_destroy(self, to_rt_uuid, callback, app_id, actor_ids):
        """ Destroys an application with remote actors on to_rt_uuid node
            callback: called when finished with the peer's respons as argument
            app_id: the application to destroy
            actor_ids: optional list of actors to destroy
        """
        if self.network.link_request(to_rt_uuid):
            # Already have link just continue in _app_destroy
            self._app_destroy(to_rt_uuid, callback, app_id, actor_ids, status=response.CalvinResponse(True))
        else:
            # Request link before continue in _app_destroy
            self.node.network.link_request(to_rt_uuid, CalvinCB(self._app_destroy,
                                                        to_rt_uuid=to_rt_uuid,
                                                        callback=callback,
                                                        app_id=app_id,
                                                        actor_ids=actor_ids))
    def _app_destroy(self, to_rt_uuid, callback, app_id, actor_ids, status, peer_node_id=None, uri=None):
        """ Got link? continue app destruction """
        if status:
            msg = {'cmd': 'APP_DESTROY', 'app_uuid': app_id, 'actor_uuids': actor_ids}
            self.network.links[to_rt_uuid].send_with_reply(callback, msg)
        elif callback:
            callback(status=status)

    def app_destroy_handler(self, payload):
        """ Peer request destruction of app and its actors """
        reply = self.node.app_manager.destroy_request(payload['app_uuid'],
                                                      payload['actor_uuids'] if 'actor_uuids' in payload else [])
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
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
            tunnel = CalvinTunnel(self.network.links, self.tunnels, None, tunnel_type, policy, rt_id=self.node.id)
            self.network.link_request(to_rt_uuid, CalvinCB(self._tunnel_link_request_finished, tunnel=tunnel, to_rt_uuid=to_rt_uuid, tunnel_type=tunnel_type, policy=policy))
            return tunnel

        # Do we have a tunnel already?
        tunnel = self._get_tunnel(to_rt_uuid, tunnel_type = tunnel_type)
        if tunnel != None:
            return tunnel

        # Create new tunnel and send request to peer
        tunnel = CalvinTunnel(self.network.links, self.tunnels, to_rt_uuid, tunnel_type, policy, rt_id=self.node.id)
        self._tunnel_new_msg(tunnel, to_rt_uuid, tunnel_type, policy)
        return tunnel

    def _get_tunnel(self, peer_node_id, tunnel_type=None):
        try:
            return [t for t in self.tunnels[peer_node_id].itervalues() if t.tunnel_type == tunnel_type][0]
        except:
            return None

    def _tunnel_new_msg(self, tunnel, to_rt_uuid, tunnel_type, policy):
        """ Create and send the tunnel new message """
        msg = {'cmd': 'TUNNEL_NEW', 'type': tunnel_type, 'tunnel_id': tunnel.id, 'policy': policy}
        self.network.links[to_rt_uuid].send_with_reply(CalvinCB(tunnel._setup_ack), msg)

    def _tunnel_link_request_finished(self, status, tunnel, to_rt_uuid, tunnel_type, policy, peer_node_id=None, uri=None):
        """ Got a link, now continue with tunnel setup """
        _log.analyze(self.rt_id, "+" , {'status': status.__str__()}, peer_node_id=to_rt_uuid)
        try:
            self.network.link_check(to_rt_uuid)
        except:
            # For some reason we still did not have a link
            raise Exception("ERROR_UNKNOWN_RUNTIME")

        # Set the link and send request for new tunnel
        tunnel._late_link(to_rt_uuid)
        self._tunnel_new_msg(tunnel, to_rt_uuid, tunnel_type, policy)
        return None

    def tunnel_new_handler(self, payload):
        """ Create a new tunnel (response side) """
        tunnel = self._get_tunnel(payload['from_rt_uuid'], payload['type'])
        ok = False
        _log.analyze(self.rt_id, "+", payload, peer_node_id=payload['from_rt_uuid'])
        if tunnel:
            _log.analyze(self.rt_id, "+ PENDING", payload, peer_node_id=payload['from_rt_uuid'])
            # Got tunnel new request while we already have one pending
            # it is not allowed to send new request while a tunnel is working
            if tunnel.status != CalvinTunnel.STATUS.WORKING:
                ok = True
                # The one with lowest tunnel id loose
                if tunnel.id < payload['tunnel_id']:
                    # Our tunnel has lowest id, change our tunnels id
                    # update status and call proper callbacks
                    # but send tunnel reply first, to get everything in order
                    msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': response.CalvinResponse(ok, data={'tunnel_id': payload['tunnel_id']}).encode()}
                    self.network.links[payload['from_rt_uuid']].send(msg)
                    tunnel._setup_ack(response.CalvinResponse(True, data={'tunnel_id': payload['tunnel_id']}))
                    _log.analyze(self.rt_id, "+ CHANGE ID", payload, peer_node_id=payload['from_rt_uuid'])
                else:
                    # Our tunnel has highest id, keep our id
                    # update status and call proper callbacks
                    # but send tunnel reply first, to get everything in order
                    msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': response.CalvinResponse(ok, data={'tunnel_id': tunnel.id}).encode()}
                    self.network.links[payload['from_rt_uuid']].send(msg)
                    tunnel._setup_ack(response.CalvinResponse(True, data={'tunnel_id': tunnel.id}))
                    _log.analyze(self.rt_id, "+ KEEP ID", payload, peer_node_id=payload['from_rt_uuid'])
            else:
                # FIXME if this happens need to decide what to do
                _log.analyze(self.rt_id, "+ DROP FIXME", payload, peer_node_id=payload['from_rt_uuid'])
            return
        else:
            # No simultaneous tunnel requests, lets create it...
            tunnel = CalvinTunnel(self.network.links, self.tunnels, payload['from_rt_uuid'], payload['type'], payload['policy'], rt_id=self.node.id, id=payload['tunnel_id'])
            _log.analyze(self.rt_id, "+ NO SMASH", payload, peer_node_id=payload['from_rt_uuid'])
            try:
                # ... and see if the handler wants it
                ok = self.tunnel_handlers[payload['type']](tunnel)
            except:
                pass
        # Send the response
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': response.CalvinResponse(ok, data={'tunnel_id': tunnel.id}).encode()}
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
            tunnel = self.tunnels[to_rt_uuid][tunnel_uuid]
        except:
            raise Exception("ERROR_UNKNOWN_TUNNEL")
            _log.analyze(self.rt_id, "+ ERROR_UNKNOWN_TUNNEL", None)
        # It exist, lets request its destruction
        msg = {'cmd': 'TUNNEL_DESTROY', 'tunnel_id': tunnel.id}
        self.network.links[to_rt_uuid].send_with_reply(CalvinCB(tunnel._destroy_ack), msg)

    def tunnel_destroy_handler(self, payload):
        """ Destroy tunnel (response side) """
        try:
            self.network.link_check(payload['to_rt_uuid'])
        except:
            raise Exception("ERROR_UNKNOWN_RUNTIME")
        try:
            tunnel = self.tunnels[payload['from_rt_uuid']][payload['tunnel_id']]
        except:
            raise Exception("ERROR_UNKNOWN_TUNNEL")
            _log.analyze(self.rt_id, "+ ERROR_UNKNOWN_TUNNEL", payload, peer_node_id=payload['from_rt_uuid'])
        # We have the tunnel so close it
        tunnel.close(local_only=True)
        ok = False
        try:
            # Hope the tunnel don't mind,
            # TODO since the requester likely don't know what to do and we have already closed it
            ok = tunnel.down_handler()
        except:
            pass
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': response.CalvinResponse(ok).encode()}
        self.network.links[payload['from_rt_uuid']].send(msg)

    def tunnel_data_handler(self, payload):
        """ Map received data over tunnel to the correct link and tunnel """
        try:
            tunnel = self.tunnels[payload['from_rt_uuid']][payload['tunnel_id']]
        except:
            _log.analyze(self.rt_id, "+ ERROR_UNKNOWN_TUNNEL", payload, peer_node_id=payload['from_rt_uuid'])
            raise Exception("ERROR_UNKNOWN_TUNNEL")
        try:
            tunnel.recv_handler(payload['value'])
        except Exception as e:
            _log.exception("Check error in tunnel recv handler")
            _log.analyze(self.rt_id, "+ EXCEPTION TUNNEL RECV HANDLER", {'payload': payload, 'exception': str(e)},
                                                                peer_node_id=payload['from_rt_uuid'], tb=True)

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
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
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
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.links[payload['from_rt_uuid']].send(msg)

if __name__ == '__main__':
    import pytest
    pytest.main("-vs runtime/north/tests/test_calvin_proto.py")
