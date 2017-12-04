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
import json
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
import calvin.requests.calvinresponse as response
from calvin.utilities.attribute_resolver import AttributeResolver
from calvin.csparser.port_property_syntax import list_port_property_capabilities
from calvin.utilities.requirement_matching import ReqMatch
from calvin.utilities import calvinconfig

_log = get_logger(__name__)
_conf = calvinconfig.get()

class PeerNode(object):

    def __init__(self, node, peer_id, attributes, capabilities, port_property_capability):
        self.node = node
        self.id = peer_id
        self.attributes = AttributeResolver(json.loads(attributes))
        self.capabilities = capabilities
        self.port_property_capability = port_property_capability

    def add_node(self, cb):
        try:
            for c in list_port_property_capabilities(which=self.port_property_capability):
                self.node.storage.add_index(['node', 'capabilities', c], self.id, root_prefix_level=3)
            for c in self.capabilities:
                self.node.storage.add_index(['node', 'capabilities', c], self.id, root_prefix_level=3)
        except Exception as e:
            _log.error("Failed to set capabilities %s" % e)

        public = None
        indexed_public = None
        indexes = self.attributes.get_indexed_public()
        for index in indexes:
            self.node.storage.add_index(index, self.id)
        public = self.attributes.get_public()
        indexed_public = self.attributes.get_indexed_public(as_list=False)

        self.node.storage.set(prefix="node-", key=self.id,
                    value={"proxy": self.node.id,
                    "uris": None,
                    "control_uris": None,
                    "attributes": {'public': public,
                    'indexed_public': indexed_public}},
                    cb=cb)

    def remove_node(self):
        self.node.storage.delete(prefix="node-", key=self.id, cb=None)
        try:
            for c in list_port_property_capabilities(which=self.port_property_capability):
                self.node.storage.remove_index(['node', 'capabilities', c], self.id)
            for c in self.capabilities:
                self.node.storage.remove_index(['node', 'capabilities', c], self.id)
            for index in self.attributes.get_indexed_public():
                self.node.storage.remove_index(index, self.id)
        except Exception as e:
            _log.error("Failed to remove index %s" % e)

class ProxyHandler(object):

    def __init__(self, node):
        self.node = node
        self.tunnels = {}
        self.peers = {}
        self._proxy_cmds = {'CONFIG': self.handle_config,
                            'REQ_MATCH': self.handle_req_match,
                            'WILL_SLEEP': self.handle_will_sleep,
                            'WAKEUP': self.handle_wakeup,
                            'GET_ACTOR_MODULE': self.handle_get_actor_module,
                            'DESTROY_REPLY' : self.handle_destroy_reply}
        self.node.proto.register_tunnel_handler('proxy', CalvinCB(self.tunnel_request_handler))

    def tunnel_request_handler(self, tunnel):
        """ Incoming tunnel request for proxy server"""
        self.tunnels[tunnel.peer_node_id] = tunnel
        tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
        tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
        tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
        return True

    def tunnel_down(self, tunnel):
        """ Callback that the tunnel is not accepted or is going down """
        del self.tunnels[tunnel.peer_node_id]
        return True

    def tunnel_up(self, tunnel):
        """ Callback that the tunnel is working """
        return True

    def tunnel_recv_handler(self, tunnel, payload):
        """ Gets called when a proxy client request """
        if 'cmd' in payload and payload['cmd'] in self._proxy_cmds:
            self._proxy_cmds[payload['cmd']](tunnel=tunnel, payload=payload)
        else:
            _log.error("Unknown proxy request %s" % payload['cmd'] if 'cmd' in payload else "")

    def _proxy_send_reply(self, tunnel, msgid, value):
        data = {'cmd': 'REPLY', 'msg_uuid': msgid, 'value': value}
        tunnel.send(data)

    def handle_config_cb(self, key, value, tunnel, msgid):
        if not value:
            self._proxy_send_reply(tunnel, msgid, response.CalvinResponse(response.INTERNAL_ERROR, {'peer_node_id': key}).encode())
            return
        self._proxy_send_reply(tunnel, msgid, response.CalvinResponse(response.OK, {'time': time.time()}).encode())

    def handle_config(self, tunnel, payload):
        """
        Store node
        """
        _log.info("Constrained runtime '%s' connected" % tunnel.peer_node_id)

        if tunnel.peer_node_id in self.peers:
            self.peers[tunnel.peer_node_id].remove_index()

        peer = PeerNode(self.node,
            tunnel.peer_node_id,
            payload['attributes'],
            payload['capabilities'],
            payload['port_property_capability'])

        peer.add_node(cb=CalvinCB(self.handle_config_cb, tunnel=tunnel, msgid=payload['msg_uuid']))
        self.peers[tunnel.peer_node_id] = peer

    def handle_will_sleep(self, tunnel, payload):
        """
        Handle sleep request
        """
        _log.info("Constrained runtime '%s' enterring sleep for %s seconds" % (tunnel.peer_node_id, payload['time']))
        link = tunnel.network.link_get(tunnel.peer_node_id)
        if link is None:
            _log.error("Proxy link does not exist")
        else:
            self._proxy_send_reply(tunnel, payload['msg_uuid'], response.CalvinResponse(response.OK).encode())
            link.set_peer_insleep()

    def handle_wakeup(self, tunnel, payload):
        """
        Handle peer wakeup
        """
        _log.info("Constrained runtime '%s' awake" % tunnel.peer_node_id)
        self._proxy_send_reply(tunnel, payload['msg_uuid'], response.CalvinResponse(response.OK, {'time': time.time()}).encode())

    def handle_req_match_cb(self, status, possible_placements, actor_id, max_placements, tunnel, msgid):
        if not possible_placements:
            self._proxy_send_reply(tunnel,
                msgid,
                response.CalvinResponse(response.NOT_FOUND, {'actor_id': actor_id}).encode())
            return
        pp = list(possible_placements)
        self._proxy_send_reply(tunnel,
            msgid,
            response.CalvinResponse(response.OK, {'actor_id': actor_id, 'possible_placements': pp[:max_placements]}).encode())

    def handle_req_match(self, tunnel, payload):
        actor_id = payload['actor_id']
        r = ReqMatch(self.node, callback=CalvinCB(self.handle_req_match_cb,
            actor_id=actor_id,
            max_placements=payload['max_placements'],
            tunnel=tunnel,
            msgid=payload['msg_uuid']))
        r.match(payload['requirements'], actor_id=actor_id)

    def handle_get_actor_module(self, tunnel, payload):
        ok = False
        actor_type = payload['actor_type']
        data = None
        path = _conf.get(None, 'compiled_actors_path')
        if path is None:
            _log.error("compiled_actors_path not set")
        else:
            if payload['compiler'] == 'mpy-cross':
                try:
                    path = path + '/mpy-cross/' + actor_type.replace('.', '/') + '.mpy'
                    f = open(path, 'rb')
                    data = f.read()
                    f.close()
                    ok = True
                except IOError as e:
                    _log.error("Failed to open '%s'" % path)
            else:
                _log.error("Unknown compiler '%s'" % payload['compiler'])

        if ok:
            self._proxy_send_reply(tunnel,
                payload['msg_uuid'],
                response.CalvinResponse(response.OK, {'actor_type': actor_type, 'module': data}).encode())
        else:
            self._proxy_send_reply(tunnel,
                payload['msg_uuid'],
                response.CalvinResponse(response.INTERNAL_ERROR, {'actor_type': actor_type, 'module': None}).encode())

    def get_capabilities(self, peer_id):
        if peer_id in self.peers:
            return self.peers[peer_id].capabilities
        return []

    def handle_destroy_reply(self, tunnel, payload):
        try:
            peer = self.peers[tunnel.peer_node_id]
            peer.remove_node()
            del self.peers[tunnel.peer_node_id]
        except Exception as e:
            _log.error("Failed to remove %s %s" % (tunnel.peer_node_id, e))

    def destroy(self, peer_id, method):
        try:
            tunnel = self.tunnels[peer_id]
            tunnel.send({"cmd": "DESTROY", "method": method})
        except Exception as e:
            _log.error("Failed to destroy %s %s" % (peer_id, e))
