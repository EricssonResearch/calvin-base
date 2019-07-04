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


import uuid
import socket
from urllib.parse import urlparse


from calvin.runtime.north.plugins.storage.storage_base import StorageBase
from calvin.runtime.south import asynchronous
from calvin.common import calvinlogger
from calvin.common import calvinconfig
from calvin.common.calvin_callback import CalvinCB
from calvin.common import calvinresponse

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)


class RegistryTunnelProvider(object):
    def __init__(self, name, cmd_map):
        super(RegistryTunnelProvider, self).__init__()
        self.name = name
        self.cmd_map = cmd_map
        self.tunnel = None
        self.max_retries = _conf.get('global', 'storage_retries') or -1
        self.retries = 0
    
    def start(self, network, uri, proto, callback=None):
        self.network = network
        self.uri = uri
        self.proto = proto
        o = urlparse(self.uri)
        fqdn = socket.getfqdn(o.hostname)
        self._server_node_name = fqdn.encode('ascii').decode('unicode-escape') # TODO: Really?
        self.network.join([self.uri],
                               callback=CalvinCB(self._start_link_cb, org_cb=callback),
                               corresponding_server_node_names=[self._server_node_name])

    def _got_link(self, peer_node_id, org_cb):
        _log.debug("_got_link %s, %s" % (peer_node_id, org_cb))
        self.tunnel = self.proto.tunnel_new(peer_node_id, self.name, {})
        self.tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, org_cb=org_cb))
        self.tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, org_cb=org_cb))
        self.tunnel.register_recv(self.tunnel_recv_handler)

    def _start_link_cb(self, status, uri, peer_node_id, org_cb):
        if status != 200:
            self.retries += 1

            if self.max_retries - self.retries != 0:
                delay = 0.5 * self.retries if self.retries < 20 else 10
                _log.info("Link to proxy failed, retrying in {}".format(delay))
                asynchronous.DelayedCall(delay, self.network.join,
                    [self.uri], callback=CalvinCB(self._start_link_cb, org_cb=org_cb),
                    corresponding_server_node_names=[self._server_node_name])
                return
            else :
                _log.info("Link to proxy still failing, giving up")
                if org_cb:
                    org_cb(False)
                return

        # Got link set up tunnel
        self._got_link(peer_node_id, org_cb)

    def tunnel_down(self, org_cb):
        """ Callback that the tunnel is not accepted or is going down """
        self.tunnel = None
        # FIXME assumes that the org_cb is the callback given by storage when starting, can only be called once
        # not future up/down
        if org_cb:
            org_cb(value=calvinresponse.CalvinResponse(False))
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self, org_cb):
        """ Callback that the tunnel is working """
        # FIXME assumes that the org_cb is the callback given by storage when starting, can only be called once
        # not future up/down
        if org_cb:
            org_cb(value=calvinresponse.CalvinResponse(True))
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_recv_handler(self, payload):
        """ Gets called when a peer replies"""
        try:
            cmd = payload['cmd']
        except:
            _log.error("Missing 'cmd' in payload")
            return
        cmd_handler = self.cmd_map.get(cmd, self._bad_command)
        cmd_handler(payload)

    def _bad_command(self, payload):    
        _log.error(f"{self.__class__.__name__} received unknown command {payload['cmd']}")
                    
    def send(self, msg):
        if not self.tunnel:
            _log.error(f"{self.__class__.__name__} send called but no tunnel connected")
            return
        self.tunnel.send(msg)
    

class ProxyRegistryClient(StorageBase):
    """
    Implements a storage that asks a master node, this is the client class
    args: node (for tunnel), host (master uri) 
    """
    def __init__(self, node, host):
        super(ProxyRegistryClient, self).__init__()
        self.tunnel_provider = RegistryTunnelProvider('storage', {'REPLY': self.reply_handler})
        self.network = node.network
        self.host = host
        self.proto = node.proto 
        self.node_id = node.id
        self.replies = {}
        _log.info("PROXY init for %s", host)
        
    def start(self, callback):
        """
            Starts the service if its needed for the storage service
            cb  is the callback called when the start is finished
        """
        self.tunnel_provider.start(self.network, self.host, self.proto, callback)

    def _send(self, cmd, msg, cb):
        msg_id = str(uuid.uuid4())
        if cb:
            self.replies[msg_id] = cb
        msg['msg_uuid'] = msg_id
        payload = dict(msg, cmd=cmd, msg_uuid=msg_id)
        self.tunnel_provider.send(payload)

    def set(self, key, value, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'key': key, 'value': value})
        self._send(cmd='SET',msg={'key':key, 'value': value}, cb=cb)

    def get(self, key, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'key': key})
        self._send(cmd='GET',msg={'key':key}, cb=cb)

    def delete(self, key, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'key': key})
        self._send(cmd='DELETE',msg={'key':key}, cb=cb)

    def add_index(self, indexes, value, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'indexes': indexes, 'value': value})
        self._send(cmd='ADD_INDEX', msg={'index': indexes, 'value': value}, cb=cb)

    def remove_index(self, indexes, value, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'indexes': indexes, 'value': value})
        self._send(cmd='REMOVE_INDEX',msg={'index': indexes, 'value': value}, cb=cb)

    def get_index(self, indexes, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'index': indexes})
        self._send(cmd='GET_INDEX',msg={'index': indexes}, cb=cb)
        
    def reply_handler(self, payload):
        if 'msg_uuid' not in payload or payload['msg_uuid'] not in self.replies:
            # if msg_uuid not in replies => caller did not care about reply
            return
        kwargs = {}
        if 'key' in payload:
            kwargs['key'] = payload['key']
        if 'value' in payload:
            kwargs['value'] = payload['value']
        if 'response' in payload:
            kwargs['value'] = calvinresponse.CalvinResponse(encoded=payload['response'])
        callback = self.replies.pop(payload['msg_uuid'])
        callback(**kwargs)
        

