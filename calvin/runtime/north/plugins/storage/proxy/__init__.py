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

from calvin.runtime.north.plugins.storage.storage_base import StorageBase
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinuuid

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)


class StorageProxy(StorageBase):
    """ Implements a storage that asks a master node, this is the client class"""
    def __init__(self, node):
        self.master_uri = _conf.get(None, 'storage_proxy')
        self.node = node
        self.tunnel = None
        self.replies = {}
        _log.debug("PROXY init for %s", self.master_uri)
        super(StorageProxy, self).__init__()

    def start(self, iface='', network='', bootstrap=[], cb=None, name=None, nodeid=None):
        """
            Starts the service if its needed for the storage service
            cb  is the callback called when the start is finished
        """
        _log.debug("PROXY start")
        self.node.network.join([self.master_uri], CalvinCB(self._start_link_cb, org_cb=cb))

    def _start_link_cb(self, status, uri, peer_node_id, org_cb):
        _log.analyze(self.node.id, "+", {'status': str(status)}, peer_node_id=peer_node_id)
        if status == "NACK":
            if org_cb:
                org_cb(False)
            return
        # Got link set up tunnel
        self.master_id = peer_node_id
        self.tunnel = self.node.proto.tunnel_new(self.master_id, 'storage', {})
        self.tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, org_cb=org_cb))
        self.tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, org_cb=org_cb))
        self.tunnel.register_recv(self.tunnel_recv_handler)

    def tunnel_down(self, org_cb):
        """ Callback that the tunnel is not accepted or is going down """
        if not self.tunnel:
            return True
        _log.analyze(self.node.id, "+ CLIENT", {'tunnel_id': self.tunnel.id})
        self.tunnel = None
        # FIXME assumes that the org_cb is the callback given by storage when starting, can only be called once
        # not future up/down
        if org_cb:
            org_cb(False)
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self, org_cb):
        """ Callback that the tunnel is working """
        if not self.tunnel:
            return True
        _log.analyze(self.node.id, "+ CLIENT", {'tunnel_id': self.tunnel.id})
        # FIXME assumes that the org_cb is the callback given by storage when starting, can only be called once
        # not future up/down
        if org_cb:
            org_cb(True)
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_recv_handler(self, payload):
        """ Gets called when a storage master replies"""
        _log.analyze(self.node.id, "+ CLIENT", {'payload': payload})
        if 'msg_uuid' in payload and payload['msg_uuid'] in self.replies and 'cmd' in payload and payload['cmd']=='REPLY':
            self.replies.pop(payload['msg_uuid'])(**{k: v for k, v in payload.iteritems() if k in ('key', 'value')})

    def send(self, cmd, msg, cb):
        msg_id = calvinuuid.uuid("MSGID")
        self.replies[msg_id] = cb
        msg['msg_uuid'] = msg_id
        self.tunnel.send(dict(msg, cmd=cmd, msg_uuid=msg_id))

    def set(self, key, value, cb=None):
        """
            Set a key, value pair in the storage
        """
        _log.analyze(self.node.id, "+ CLIENT", {'key': key, 'value': value})
        self.send(cmd='SET',msg={'key':key, 'value': value}, cb=cb)

    def get(self, key, cb=None):
        """
            Gets a value from the storage
        """
        _log.analyze(self.node.id, "+ CLIENT", {'key': key})
        self.send(cmd='GET',msg={'key':key}, cb=cb)

    def get_concat(self, key, cb=None):
        """
            Gets a value from the storage
        """
        _log.analyze(self.node.id, "+ CLIENT", {'key': key})
        self.send(cmd='GET_CONCAT',msg={'key':key}, cb=cb)

    def append(self, key, value, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", {'key': key, 'value': value})
        self.send(cmd='APPEND',msg={'key':key, 'value': value}, cb=cb)

    def remove(self, key, value, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", {'key': key, 'value': value})
        self.send(cmd='REMOVE',msg={'key':key, 'value': value}, cb=cb)

    def bootstrap(self, addrs, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", None)

    def stop(self, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", None)
        if cb:
            cb()