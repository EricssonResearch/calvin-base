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

import time
from calvin.utilities import calvinuuid
from calvin.utilities.utils import enum
from calvin.utilities.calvin_callback import CalvinCB, CalvinCBClass
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
from calvin.utilities import proxyconfig
import calvin.requests.calvinresponse as response

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()
_sec_conf = _conf.get("security", "security_conf")


def send_message(peer_id, link, msg, callback=None, status=None, **kwargs):
    # Re send kwargs ?!
    if status or status is None:
        try:
            if 'value' in msg and 'status' in msg['value'] and msg['value']['status'] not in msg['value']['success_list']:
                _log.warning("Failure message %s to peer_id %s", msg, peer_id)
            if status and 'value' not in msg:
                msg['value'] = status.encode()
            if callback is None:
                link.send(msg)
            else:
                link.send_with_reply(callback, msg)
        except Exception as e:
            error = "Failed to send data to {} on a link, msg => {}".format(peer_id, repr(msg))
            _log.exception(error)
            if callback:
                callback(status=response.CalvinResponse(False, data={'info': error, 'exc': str(e)}))
    elif not status and status is not None:
        # Maybe always send message buy with negtive status
        _log.error("Negative status %s for send message %s to %s", str(status), msg, peer_id)
        msg['value'] = status.encode()
        if callback:
            callback(status=status)

def forward_message(peer_id, link, payload, status=None):
    if status or status is None:
        try:
            link.transport.send(payload)
        except Exception as e:
            _log.exception("Failed to forward data to {} on a link, msg => {}".format(peer_id, repr(payload)))


class CalvinTunnel(object):
    """CalvinTunnel is a tunnel over the runtime to runtime communication with a peer node"""

    STATUS = enum('PENDING', 'WORKING', 'TERMINATED')

    def __init__(self, network, tunnels, peer_node_id, tunnel_type, policy, rt_id=None, id=None):
        """ links: the calvin networks dictionary of links
            peer_node_id: the id of the peer that we use
            tunnel_type: what is the usage of the tunnel
            policy: TODO not used currently
            id: Tunnel objects on both nodes will use the same id number hence only supply if provided from other side
        """
        super(CalvinTunnel, self).__init__()
        # The tunnel only use one link (links[peer_node_id]) at a time but it can switch at any point
        self.network = network
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
                self.tunnels[self.peer_node_id][self.id] = self
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
                self.tunnels[self.peer_node_id][self.id] = self
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
        self.tunnels[self.peer_node_id][self.id] = self

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
        def _failed_to_send(payload, status):
            _log.analyze(self.rt_id, "+ TUNNEL FAILED", payload, peer_node_id=self.peer_node_id)

        msg = {'cmd': 'TUNNEL_DATA', 'value': payload, 'tunnel_id': self.id}
        self.network.link_request(self.peer_node_id, callback=CalvinCB(send_message, msg=msg, callback=CalvinCB(_failed_to_send, payload)))

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
            'PROXY_CONFIG': [CalvinCB(self.proxy_config_handler)],
            'SLEEP_REQUEST': [CalvinCB(self.proxy_sleep_request_handler)],
            'ACTOR_NEW': [CalvinCB(self.actor_new_handler)],
            'ACTOR_MIGRATE': [CalvinCB(self.actor_migrate_handler)],
            'APP_DESTROY': [CalvinCB(self.app_destroy_handler)],
            'PORT_CONNECT': [CalvinCB(self.port_connect_handler)],
            'PORT_DISCONNECT': [CalvinCB(self.port_disconnect_handler)],
            'PORT_REMOTE_CONNECT': [CalvinCB(self.port_remote_connect_handler)],
            'TUNNEL_NEW': [CalvinCB(self.tunnel_new_handler)],
            'TUNNEL_DESTROY': [CalvinCB(self.tunnel_destroy_handler)],
            'TUNNEL_DATA': [CalvinCB(self.tunnel_data_handler)],
            'REPLY': [CalvinCB(self.reply_handler)],
            'AUTHENTICATION_DECISION': [CalvinCB(self.authentication_decision_handler)],
            'AUTHORIZATION_REGISTER': [CalvinCB(self.authorization_register_handler)],
            'AUTHORIZATION_DECISION': [CalvinCB(self.authorization_decision_handler)],
            'AUTHORIZATION_SEARCH': [CalvinCB(self.authorization_search_handler)]})

        self.rt_id = node.id
        self.node = node
        self.network = network
        # Register the function that receives all incoming messages
        self.network.register_recv(self.recv_handler)
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
        link = self.network.link_get(payload['from_rt_uuid'])
        if link:
            link.reply_handler(payload)
        else:
            _log.error("Got reply from unknown or disconnected link %s", payload['from_rt_uuid'])
            # Maybe do a link request here ?

    def while_quitting(self, tp_link, payload):
        """ A generic handling of responses while quitting the node
        """
        if not self.node.quitting:
            return False
        # If generic handling of command is not possible or the method
        # is accepted during quitting it is left out from dict.
        resp = {
            'PROXY_CONFIG': response.INTERNAL_ERROR,
            'ACTOR_NEW': response.INTERNAL_ERROR,
            'ACTOR_MIGRATE': response.NOT_FOUND,
            'APP_DESTROY': response.NOT_FOUND,
            'PORT_CONNECT': response.NOT_FOUND,
            'PORT_REMOTE_CONNECT': response.NOT_FOUND,
            'TUNNEL_NEW': response.INTERNAL_ERROR,
            'AUTHENTICATION_DECISION': response.INTERNAL_ERROR,
            'AUTHORIZATION_REGISTER': response.NOT_FOUND,
            'AUTHORIZATION_DECISION': response.NOT_FOUND,
            'AUTHORIZATION_SEARCH': response.INTERNAL_ERROR
        }
        if payload['cmd'] not in resp:
            return False
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': response.CalvinResponse(resp[payload['cmd']]).encode()}
        self.network.link_request(payload['from_rt_uuid'], CalvinCB(send_message, msg=msg))
        return True

    def recv_handler(self, tp_link, payload):
        """ Called by transport when a full payload has been received
        """
        _log.analyze(self.rt_id, "RECV", payload)
        link = self.network.link_get(payload['from_rt_uuid'])
        if link is None:
            # TODO: Create own exception here
            raise Exception("ERROR_UNKNOWN_RUNTIME")

        if payload['to_rt_uuid'] == self.rt_id:
            if not ('cmd' in payload and payload['cmd'] in self.callback_valid_names()):
                raise Exception("ERROR_UNKOWN_COMMAND")
            if self.while_quitting(tp_link, payload):
                return
            # Call the proper handler for the command using CalvinCBClass
            self._callback_execute(payload['cmd'], payload)
        else:
            # Get/request a link to destination and forward message
            self.network.link_request(payload['to_rt_uuid'], CalvinCB(forward_message, payload=payload))

    #
    # Remote commands supported by protocol
    #

    #### PROXY NODES ####

    def proxy_config_handler(self, payload):
        """ Configure a node using this node as a proxyconfig
        """
        proxyconfig.set_proxy_config(payload['from_rt_uuid'],
            payload['capabilities'],
            payload['port_property_capability'],
            self.network.link_get(payload['from_rt_uuid']),
            self.node.storage,
            CalvinCB(self.node.network.link_request, payload['from_rt_uuid'],
                callback=CalvinCB(send_message, msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'time': time.time()})),
            payload.get('attributes'))

    def proxy_sleep_request_handler(self, payload):
        """ Handle node requesting sleep mode
        """
        proxyconfig.handle_sleep_request(payload['from_rt_uuid'],
            self.network.link_get(payload['from_rt_uuid']),
            payload['seconds_to_sleep'],
            CalvinCB(self.node.network.link_request, payload['from_rt_uuid'],
                callback=CalvinCB(send_message, msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid']})))

    #### ACTORS ####

    def actor_new(self, to_rt_uuid, callback, actor_type, state, prev_connections):
        """ Creates a new actor on to_rt_uuid node, but is only intended for migrating actors
            callback: called when finished with the peers respons as argument
            actor_type: see actor manager
            state: see actor manager
            prev_connections: see actor manager
        """
        self.node.network.link_request(to_rt_uuid, CalvinCB(send_message,
                                                            msg = {'cmd': 'ACTOR_NEW',
                                                                   'state': {'actor_type': actor_type, 'actor_state': state, 'prev_connections': prev_connections}},
                                                            callback=callback))

    def actor_new_handler(self, payload):
        """ Peer request new actor with state and connections """
        _log.analyze(self.rt_id, "+", payload, tb=True)
        self.node.am.new_from_migration(payload['state']['actor_type'],
                                        payload['state']['actor_state'],
                                        payload['state']['prev_connections'],
                                        callback=CalvinCB(self.node.network.link_request, payload['from_rt_uuid'], callback=CalvinCB(send_message,
                                            msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid']})))

    def actor_migrate(self, to_rt_uuid, callback, actor_id, requirements, extend=False, move=False):
        """ Request actor on to_rt_uuid node to migrate accoring to new deployment requirements
            callback: called when finished with the status respons as argument
            actor_id: actor_id to migrate
            requirements: see app manager
            extend: if extending current deployment requirements
            move: if prefers to move from node
        """
        self.node.network.link_request(to_rt_uuid, CalvinCB(send_message,
            msg = {'cmd': 'ACTOR_MIGRATE',
                'requirements': requirements, 'actor_id': actor_id, 'extend': extend, 'move': move},
            callback=callback))

    def actor_migrate_handler(self, payload):
        """ Peer request new actor with state and connections """
        self.node.am.update_requirements(payload['actor_id'], payload['requirements'],
                                         payload['extend'], payload['move'],
                                         callback=CalvinCB(self.node.network.link_request, payload['from_rt_uuid'], callback=CalvinCB(send_message,
                                                                    msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid']})))

    #### APPS ####

    def app_destroy(self, to_rt_uuid, callback, app_id, actor_ids, **kwargs):
        """ Destroys an application with remote actors on to_rt_uuid node
            callback: called when finished with the peer's respons as argument
            app_id: the application to destroy (could be None if only actors to be destroyed)
            actor_ids: optional list of actors to destroy
            kwargs: optionally take
                'disconnect': True/False to disconnect actors first
        """
        # Request link before continue in _app_destroy
        msg = {'cmd': 'APP_DESTROY', 'app_uuid': app_id, 'actor_uuids': actor_ids}
        msg.update(kwargs)
        self.node.network.link_request(to_rt_uuid, CalvinCB(send_message,
            msg=msg,
            callback=callback))

    def app_destroy_handler(self, payload):
        """ Peer request destruction of app and its actors """
        replication_id = payload.get('replication_id', None)
        if payload.get('disconnect', False):
            self.node.app_manager.destroy_request_with_disconnect(payload['app_uuid'],
                  payload['actor_uuids'] if 'actor_uuids' in payload else [],
                  payload['disconnect'],
                  callback=CalvinCB(self.node.network.link_request, payload['from_rt_uuid'], callback=CalvinCB(send_message,
                                    msg={'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid']})))
            if replication_id is not None:
                for actor_id in payload.get('actor_uuids', []):
                    self.node.storage.remove_replica_node(replication_id, actor_id)
        else:
            reply = self.node.app_manager.destroy_request(payload['app_uuid'],
                                                          payload['actor_uuids'] if 'actor_uuids' in payload else [])
            msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
            self.node.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

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
        link = self.network.link_get(to_rt_uuid)
        if not link:
            # Need to join the other peer first
            # Create a tunnel object which is not inserted on a link yet
            tunnel = CalvinTunnel(self.network, self.tunnels, None, tunnel_type, policy, rt_id=self.node.id)
            self.network.link_request(to_rt_uuid,
                                      CalvinCB(self._tunnel_link_request_finished, tunnel=tunnel,
                                               to_rt_uuid=to_rt_uuid, tunnel_type=tunnel_type, policy=policy))
            return tunnel

        # Do we have a tunnel already?
        tunnel = self._get_tunnel(to_rt_uuid, tunnel_type=tunnel_type)
        if tunnel != None:
            return tunnel

        # Create new tunnel and send request to peer
        tunnel = CalvinTunnel(self.network, self.tunnels, to_rt_uuid, tunnel_type, policy, rt_id=self.node.id)
        send_message(to_rt_uuid, link,
                msg={'cmd': 'TUNNEL_NEW', 'type': tunnel_type, 'tunnel_id': tunnel.id, 'policy': policy},
                callback=CalvinCB(tunnel._setup_ack))
        return tunnel

    def _get_tunnel(self, peer_node_id, tunnel_type=None):
        try:
            return [t for t in self.tunnels[peer_node_id].itervalues() if t.tunnel_type == tunnel_type][0]
        except:
            return None

    def _tunnel_link_request_finished(self, peer_id, link, status, tunnel, to_rt_uuid, tunnel_type, policy):
        """ Got a link, now continue with tunnel setup """
        _log.analyze(self.rt_id, "+", {'status': status.__str__()}, peer_node_id=to_rt_uuid)
        link = self.network.link_get(to_rt_uuid)
        if not link or not status:
            # TODO: bad create own exception here
            # For some reason we still did not have a link
            raise Exception("ERROR_UNKNOWN_RUNTIME")

        # Set the link and send request for new tunnel
        tunnel._late_link(to_rt_uuid)
        send_message(peer_id, link,
                msg={'cmd': 'TUNNEL_NEW', 'type': tunnel_type, 'tunnel_id': tunnel.id, 'policy': policy},
                callback=CalvinCB(tunnel._setup_ack))
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
                    msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'],
                            'value': response.CalvinResponse(ok, data={'tunnel_id': payload['tunnel_id']}).encode()}
                    self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))
                    tunnel._setup_ack(response.CalvinResponse(True, data={'tunnel_id': payload['tunnel_id']}))
                    _log.analyze(self.rt_id, "+ CHANGE ID", payload, peer_node_id=payload['from_rt_uuid'])
                else:
                    # Our tunnel has highest id, keep our id
                    # update status and call proper callbacks
                    # but send tunnel reply first, to get everything in order
                    msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'],
                            'value': response.CalvinResponse(ok, data={'tunnel_id': tunnel.id}).encode()}
                    self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))
                    tunnel._setup_ack(response.CalvinResponse(True, data={'tunnel_id': tunnel.id}))
                    _log.analyze(self.rt_id, "+ KEEP ID", payload, peer_node_id=payload['from_rt_uuid'])
            else:
                # FIXME if this happens need to decide what to do
                _log.analyze(self.rt_id, "+ DROP FIXME", payload, peer_node_id=payload['from_rt_uuid'])
            return
        else:
            # No simultaneous tunnel requests, lets create it...
            tunnel = CalvinTunnel(self.network, self.tunnels, payload['from_rt_uuid'],
                                    payload['type'], payload['policy'], rt_id=self.node.id, id=payload['tunnel_id'])
            _log.analyze(self.rt_id, "+ NO SMASH", payload, peer_node_id=payload['from_rt_uuid'])
            try:
                # ... and see if the handler wants it
                ok = self.tunnel_handlers[payload['type']](tunnel)
            except:
                pass
        # Send the response
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'],
                'value': response.CalvinResponse(ok, data={'tunnel_id': tunnel.id}).encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

        # If handler did not want it close it again
        if not ok:
            tunnel.close(local_only=True)

    def tunnel_destroy(self, to_rt_uuid, tunnel_uuid):
        """ Destroy a tunnel (request side) """
        link = self.network.link_get(to_rt_uuid)
        if not link:
            raise Exception("ERROR_UNKNOWN_RUNTIME")
        try:
            tunnel = self.tunnels[to_rt_uuid][tunnel_uuid]
        except KeyError:
            _log.analyze(self.rt_id, "+ ERROR_UNKNOWN_TUNNEL", None)
            raise Exception("ERROR_UNKNOWN_TUNNEL")
        # It exist, lets request its destruction
        msg = {'cmd': 'TUNNEL_DESTROY', 'tunnel_id': tunnel.id}
        self.network.link_request(to_rt_uuid, callback=CalvinCB(send_message, msg=msg))

    def tunnel_destroy_handler(self, payload):
        """ Destroy tunnel (response side) """
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
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

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

    def port_connect(self, callback=None, port_id=None, port_properties=None, peer_port_meta=None, **kwargs):
        """ Before calling this method all needed information and when requested a tunnel must be available
            see port manager for parameters
        """
        msg = {'cmd': 'PORT_CONNECT', 'port_id': port_id, 'port_properties': port_properties,
                'peer_actor_id': peer_port_meta.actor_id, 'peer_port_name': peer_port_meta.port_name,
                'peer_port_id': peer_port_meta.port_id, 'peer_port_properties': peer_port_meta.properties}
        msg.update(kwargs)
        self.network.link_request(peer_port_meta.node_id, callback=CalvinCB(send_message, msg=msg, callback=callback))

    def port_connect_handler(self, payload):
        """ Request for port connection """
        reply = self.node.pm.connection_request(payload)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def port_disconnect(self, callback=None, port_id=None, peer_node_id=None, peer_port_id=None, peer_actor_id=None,
                        peer_port_name=None, peer_port_dir=None, **kwargs):
        """ Before calling this method all needed information must be available
            see port manager for parameters
        """
        msg = {'cmd': 'PORT_DISCONNECT', 'port_id': port_id, 'peer_actor_id': peer_actor_id,
                'peer_port_name': peer_port_name, 'peer_port_id': peer_port_id, 'peer_port_dir': peer_port_dir}
        msg.update(kwargs)
        self.network.link_request(peer_node_id, callback=CalvinCB(send_message, msg=msg, callback=callback))

    def port_disconnect_handler(self, payload):
        """ Reguest for port disconnect """
        reply = self.node.pm.disconnection_request(payload)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def port_remote_connect(self, port_id, node_id, peer_port_id, callback=None):
        self.node.network.link_request(node_id, CalvinCB(send_message,
             msg={'cmd': 'PORT_REMOTE_CONNECT', 'port_id': port_id,
                  'peer_port_id': peer_port_id},
             callback=callback))

    def port_remote_connect_handler(self, payload):
        """ Handle request for remote port connection """
        self.node.pm.connect(port_id=payload['port_id'], peer_port_id=payload['peer_port_id'],
                callback=CalvinCB(self.node.network.link_request, payload['from_rt_uuid'],
                    callback=CalvinCB(send_message, msg={'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid']})))

    #### AUTHENTICATION ####

    def authentication_decision(self, auth_server_uuid, callback, jwt):
        """
        Return a response to an authentication request.

        auth_server_uuid: node uuid for the runtime that acts as authentication server
        callback: called when finished with the authentication decision
        jwt: signed JSON Web Token (JWT) containing the authentication request
        """
        _log.debug("authentication_decision:\n\tauth_server_uuid={}\n\tcallback={}\n\tjwt={}".format(auth_server_uuid, callback, jwt))
        self.node.network.link_request(auth_server_uuid,
                                       CalvinCB(send_message,
            msg = {'cmd': 'AUTHENTICATION_DECISION', 'jwt': jwt, 'cert_name': self.node.runtime_credentials.cert_name},
                                                callback=callback))

    def authentication_decision_handler(self, payload):
        """
        Return a response to the authentication request in the payload.

        Signed JSON Web Tokens (JWT) with timestamps and information about
        sender and receiver are used for both the request and response.
        A Policy Decision Point (PDP) is used to determine if access is permitted.
        """
        _log.debug("authentication_decision_handler:\n\tpayload={}".format(payload))
        if ('authentication' in _sec_conf) and 'accept_external_requests' in _sec_conf['authentication']:
            try:
                self.node.authentication.decode_request(payload,
                                                        CalvinCB(self._authentication_decision_handler_jwt_decoded_cb,
                                                                payload=payload)
                                                        )
                return
            except Exception as err:
                _log.error("authentication_decision_handler: Failed to decode authentication request, err={}")
                reply = response.CalvinResponse(response.INTERNAL_ERROR)
                # Send reply
                msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}

            self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def _authentication_decision_handler_jwt_decoded_cb(self, decoded, payload):
        """The JWT is now decoded, let's try to authenticate the content"""
        _log.debug("authentication_decision_handler_jwt_decoded_cb:\n\tdecoded={}\n\tpayload={}".format(decoded, payload))
        self.node.authentication.adp.authenticate(decoded["request"],
                            callback=CalvinCB(self._authentication_decision_handler, payload, decoded,
                                             ))

    def _authentication_decision_handler(self, payload, request, auth_response):
        """Decision has been made, return the response"""
        _log.debug("_authentication_decision_handler:\n\tpayload={}\n\trequest={}\n\tauth_response={}".format(payload, request, auth_response))
        try:
            jwt_response = self.node.authentication.encode_response(request, auth_response)
            data_response = {"jwt": jwt_response, "cert_name": self.node.runtime_credentials.cert_name}
            reply = response.CalvinResponse(response.OK, data_response)
        except Exception:
            reply = response.CalvinResponse(response.INTERNAL_ERROR)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    #### AUTHORIZATION ####

    def authorization_register(self, authz_server_uuid, callback, jwt):
        """
        Register node attributes for authorization.

        authz_server_uuid: node uuid for the runtime that acts as authorization server
        callback: called when finished with the registration
        jwt: signed JSON Web Token (JWT) containing the node attributes
        """
        _log.debug("authorization_register:\n\tauthz_server_uuid={}\n\tcallback={}\n\tjwt={}".format(authz_server_uuid, callback, jwt))
        self.node.network.link_request(authz_server_uuid,
                                       CalvinCB(send_message,
                                                msg = {'cmd': 'AUTHORIZATION_REGISTER', 'jwt': jwt, 'cert_name': self.node.runtime_credentials.cert_name},
                                                callback=callback))

    def authorization_register_handler(self, payload):
        """
        Register node attributes in payload for authorization.

        Signed JSON Web Token (JWT) is used to send the attributes.
        """
        _log.debug("authorization_register_handler:\n\tpayload={}".format(payload))
        if not _sec_conf['authorization']['accept_external_requests']:
            reply = response.CalvinResponse(response.NOT_FOUND)
            # Send reply
            msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        else:
            try:
                self.node.authorization.decode_request(payload,
                                                      CalvinCB(self._authorization_register_handler_cb,
                                                              payload=payload))
                return
            except Exception as exc:
                _log.exception("authorization_register_handler, exc={}".format(exc))
                reply = response.CalvinResponse(response.INTERNAL_ERROR)
                # Send reply
                msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}

        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def _authorization_register_handler_cb(self, decoded, payload):
        """JWT is now decoded, register node"""
        _log.debug("_authorization_register_handler_cb:\ndecoded={}\npayload={}".format(decoded, payload))
        self.node.authorization.pdp.register_node(decoded["iss"], decoded["attributes"])
        reply = response.CalvinResponse(response.OK)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def authorization_decision(self, authz_server_uuid, callback, jwt):
        """
        Return a response to an authorization request.

        authz_server_uuid: node uuid for the runtime that acts as authorization server
        callback: called when finished with the authorization decision
        jwt: signed JSON Web Token (JWT) containing the authorization request
        """
        _log.debug("authorization_decision:\n\tauthz_server_uuid={}\n\tcallback={}\n\tjwt={}".format(authz_server_uuid, callback, jwt))
        self.node.network.link_request(authz_server_uuid,
                                       CalvinCB(send_message,
            msg = {'cmd': 'AUTHORIZATION_DECISION', 'jwt': jwt, 'cert_name': self.node.runtime_credentials.cert_name},
                                                callback=callback))

    def authorization_decision_handler(self, payload):
        """
        Return a response to the authorization request in the payload.

        Signed JSON Web Tokens (JWT) with timestamps and information about
        sender and receiver are used for both the request and response.
        A Policy Decision Point (PDP) is used to determine if access is permitted.
        """
        _log.debug("authorization_decision_handler:\n\tPayload={}".format(payload))
        if not _sec_conf['authorization']['accept_external_requests']:
            reply = response.CalvinResponse(response.NOT_FOUND)
            # Send reply
            msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        else:
            try:
                self.node.authorization.decode_request(payload,
                                                      CalvinCB(self._authorization_decision_handler_jwt_decoded_cb,
                                                               payload=payload))
                return
            except Exception as exc:
                _log.exception("authorization_decision_handler failed, exc={}".format(exc))
                reply = response.CalvinResponse(response.INTERNAL_ERROR)
                # Send reply
                msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def _authorization_decision_handler_jwt_decoded_cb(self, decoded, payload):
        """JWT is now decoded, continute with authorization decision"""
        _log.debug("_authorization_decision_handler_jwt_decoded_cb:\n\tDecoded={}\n\tPayload={}".format(decoded, payload))
        self.node.authorization.pdp.authorize(decoded["request"],
                            callback=CalvinCB(self._authorization_decision_handler, payload, decoded))

    def _authorization_decision_handler(self, payload, request, authz_response):
        """Authorization decision has been made, now send response"""
        _log.debug("_authorization_decision_handler:\n\tPayload={}\n\tRequest={}\n\tAuthz_response={}".format(payload, request, authz_response))
        try:
            jwt_response = self.node.authorization.encode_response(request, authz_response)
            data_response = {"jwt": jwt_response, "cert_name": self.node.runtime_credentials.cert_name}
            reply = response.CalvinResponse(response.OK, data_response)
        except Exception as exc:
            _log.exception("_authorization_decision_handler, exc={}".format(exc))
            reply = response.CalvinResponse(response.INTERNAL_ERROR)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def authorization_search(self, authz_server_uuid, callback, jwt):
        """
        Search for runtime where the decision for the authorization request is 'permit'.

        authz_server_uuid: node uuid for the runtime that acts as authorization server
        callback: called when finished with the search
        jwt: signed JSON Web Token (JWT) containing the authorization request
        """
        _log.debug("authorization_search:\n\tauthz_server_uuid={}\n\tcallback={}\n\tjwt={}".format(authz_server_uuid, callback, jwt))
        self.node.network.link_request(authz_server_uuid,
                                       CalvinCB(send_message,
            msg = {'cmd': 'AUTHORIZATION_SEARCH', 'jwt': jwt, 'cert_name': self.node.runtime_credentials.cert_name},
                                                callback=callback))

    def authorization_search_handler(self, payload):
        """
        Return a response to the authorization search request in the payload.

        Signed JSON Web Tokens (JWT) with timestamps and information about
        sender and receiver are used for both the request and response.
        A Policy Decision Point (PDP) is used for the authorization search.
        """
        _log.debug("authorization_search_handler:\n\tpayload={}".format(payload))
        try:
            decoded = self.node.authorization.decode_request(payload,
                                                             CalvinCB(self._authorization_search_handler_jwt_decoded_cb,
                                                                    payload=payload))
        except Exception as err:
            _log.info("Failed to decode request, err={}".format(err))
            reply = response.CalvinResponse(response.INTERNAL_ERROR)
            # Send reply
            msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
            self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def _authorization_search_handler_jwt_decoded_cb(self, decoded, payload):
        """JWT is now decoded, contintue search for runtime where actor is allowed to execute"""
        _log.debug("_authorization_search_handler_jwt_decoded:\n\tdecoded={}\n\tpayload={}".format(decoded, payload))
        try:
            self.node.authorization.pdp.runtime_search(decoded["request"], decoded["whitelist"],
                                         CalvinCB(self._authorization_search_handler, payload, decoded))
        except Exception as err:
            _log.info("Failed to decode authorization search request, err={}".format(err))
            reply = response.CalvinResponse(response.INTERNAL_ERROR)
            # Send reply
            msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
            self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))

    def _authorization_search_handler(self, payload, request, search_result):
        """Search for a candidate finished, now send response"""
        _log.debug("_authorization_search_handler:\n\tpayload={}\n\trequest={}\n\tsearch_result={}".format(payload, request, search_result))
        try:
            if search_result is None:
                runtime_id = None
                data_response = {"node_id": runtime_id}
            else:
                runtime_id = search_result[0]
                jwt_response = self.node.authorization.encode_response(request, search_result[1], runtime_id)
                data_response = {"node_id": runtime_id, "jwt": jwt_response, "cert_name": self.node.runtime_credentials.cert_name}
            reply = response.CalvinResponse(response.OK, data_response)
        except Exception:
            reply = response.CalvinResponse(response.INTERNAL_ERROR)
        # Send reply
        msg = {'cmd': 'REPLY', 'msg_uuid': payload['msg_uuid'], 'value': reply.encode()}
        self.network.link_request(payload['from_rt_uuid'], callback=CalvinCB(send_message, msg=msg))


if __name__ == '__main__':
    import pytest
    pytest.main("-vs runtime/north/tests/test_calvin_proto.py")
