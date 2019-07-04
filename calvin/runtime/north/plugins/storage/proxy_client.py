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

from calvin.runtime.north.plugins.storage.storage_base import StorageBase
from calvin.runtime.south import asynchronous
from calvin.common import calvinlogger
from calvin.common import calvinconfig
from calvin.common.calvin_callback import CalvinCB
from calvin.common import calvinresponse

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)


class RegistryTunnelProvider(object):
    def __init__(self, node, host, cmd_map):
        super(RegistryTunnelProvider, self).__init__()
        self.master_uri = host
        self.cmd_map = {'REPLY': self.reply_handler} # FIXME: Move externally
        self.max_retries = _conf.get('global', 'storage_retries') or -1
        self.retries = 0
        self.node = node
        self.node_id = node.id
        self.tunnel = None
        self.replies = {}
    
    def start(self, callback):
        from urllib.parse import urlparse
        import socket
        o = urlparse(self.master_uri)
        fqdn = socket.getfqdn(o.hostname)
        self._server_node_name = fqdn.encode('ascii').decode('unicode-escape') # TODO: Really?
        self.node.network.join([self.master_uri],
                               callback=CalvinCB(self._start_link_cb, org_cb=callback),
                               corresponding_server_node_names=[self._server_node_name])

    def _got_link(self, master_id, org_cb):
        _log.debug("_got_link %s, %s" % (master_id, org_cb))
        self.master_id = master_id
        self.tunnel = self.node.proto.tunnel_new(self.master_id, 'storage', {})
        self.tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, org_cb=org_cb))
        self.tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, org_cb=org_cb))
        self.tunnel.register_recv(self.tunnel_recv_handler)

    def _start_link_cb(self, status, uri, peer_node_id, org_cb):
        _log.analyze(self.node_id, "+", {'status': str(status)}, peer_node_id=peer_node_id)

        _log.info("status: {}, {}".format(status, str(status)))

        if status != 200:
            self.retries += 1

            if self.max_retries - self.retries != 0:
                delay = 0.5 * self.retries if self.retries < 20 else 10
                _log.info("Link to proxy failed, retrying in {}".format(delay))
                asynchronous.DelayedCall(delay, self.node.network.join,
                    [self.master_uri], callback=CalvinCB(self._start_link_cb, org_cb=org_cb),
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
        _log.info("storage proxy down")
        if not self.tunnel:
            return True
        _log.analyze(self.node_id, "+ CLIENT", {'tunnel_id': self.tunnel.id})
        self.tunnel = None
        # FIXME assumes that the org_cb is the callback given by storage when starting, can only be called once
        # not future up/down
        if org_cb:
            org_cb(value=calvinresponse.CalvinResponse(False))
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self, org_cb):
        """ Callback that the tunnel is working """
        _log.info("storage proxy up")
        if not self.tunnel:
            return True
        _log.analyze(self.node_id, "+ CLIENT", {'tunnel_id': self.tunnel.id})
        # FIXME assumes that the org_cb is the callback given by storage when starting, can only be called once
        # not future up/down
        if org_cb:
            org_cb(value=calvinresponse.CalvinResponse(True))
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_recv_handler(self, payload):
        """ Gets called when a storage master replies"""
        try:
            cmd = payload['cmd']
        except:
            _log.error("Missing 'cmd' in payload")
            return
        cmd_handler = self.cmd_map.get(cmd, self._bad_command)
        cmd_handler(payload)

    def _bad_command(self, payload):    
        _log.error(f"{self.__class__.__name__} received unknown command {payload['cmd']}")
                    
    def send(self, cmd, msg, cb):
        if not self.tunnel:
            return
        msg_id = str(uuid.uuid4())
        if cb:
            self.replies[msg_id] = cb
        msg['msg_uuid'] = msg_id
        self.tunnel.send(dict(msg, cmd=cmd, msg_uuid=msg_id))
    
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


class ProxyRegistryClient(StorageBase):
    """
    Implements a storage that asks a master node, this is the client class
    args: node (for tunnel), host (master uri) 
    """
    def __init__(self, node, host):
        super(ProxyRegistryClient, self).__init__()
        self.tunnel_provider = RegistryTunnelProvider(node, host, None)
        self.node_id = node.id
        _log.info("PROXY init for %s", host)
        
    def start(self, callback):
        """
            Starts the service if its needed for the storage service
            cb  is the callback called when the start is finished
        """
        self.tunnel_provider.start(callback)

    def set(self, key, value, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'key': key, 'value': value})
        self.tunnel_provider.send(cmd='SET',msg={'key':key, 'value': value}, cb=cb)

    def get(self, key, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'key': key})
        self.tunnel_provider.send(cmd='GET',msg={'key':key}, cb=cb)

    def delete(self, key, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'key': key})
        self.tunnel_provider.send(cmd='DELETE',msg={'key':key}, cb=cb)

    def add_index(self, indexes, value, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'indexes': indexes, 'value': value})
        self.tunnel_provider.send(cmd='ADD_INDEX', msg={'index': indexes, 'value': value}, cb=cb)

    def remove_index(self, indexes, value, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'indexes': indexes, 'value': value})
        self.tunnel_provider.send(cmd='REMOVE_INDEX',msg={'index': indexes, 'value': value}, cb=cb)

    def get_index(self, indexes, cb=None):
        _log.analyze(self.node_id, "+ CLIENT", {'index': indexes})
        self.tunnel_provider.send(cmd='GET_INDEX',msg={'index': indexes}, cb=cb)

