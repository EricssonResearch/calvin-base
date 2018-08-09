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
from calvin.runtime.south.async import async
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinuuid
from calvin.requests import calvinresponse

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)


class StorageProxy(StorageBase):
    """ Implements a storage that asks a master node, this is the client class"""
    def __init__(self, node):
        self.master_uri = _conf.get('global', 'storage_proxy')
        self.max_retries = _conf.get('global', 'storage_retries') or -1
        self.retries = 0
        self.node = node
        self.tunnel = None
        self.replies = {}
        _log.info("PROXY init for %s", self.master_uri)
        super(StorageProxy, self).__init__()

    def start(self, iface='', network='', bootstrap=[], cb=None, name=None, nodeid=None):
        """
            Starts the service if its needed for the storage service
            cb  is the callback called when the start is finished
        """
        from urlparse import urlparse
        import socket
        _log.info("PROXY start")
        o=urlparse(self.master_uri)
        fqdn = socket.getfqdn(o.hostname)
        self._server_node_name = fqdn.decode('unicode-escape')
        self.node.network.join([self.master_uri],
                               callback=CalvinCB(self._start_link_cb, org_cb=cb),
                               corresponding_server_node_names=[self._server_node_name])

    def _got_link(self, master_id, org_cb):
        _log.debug("_got_link %s, %s" % (master_id, org_cb))
        self.master_id = master_id
        self.tunnel = self.node.proto.tunnel_new(self.master_id, 'storage', {})
        self.tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, org_cb=org_cb))
        self.tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, org_cb=org_cb))
        self.tunnel.register_recv(self.tunnel_recv_handler)

    def _start_link_cb(self, status, uri, peer_node_id, org_cb):
        _log.analyze(self.node.id, "+", {'status': str(status)}, peer_node_id=peer_node_id)

        _log.info("status: {}, {}".format(status, str(status)))

        if status != 200:
            self.retries += 1

            if self.max_retries - self.retries != 0:
                delay = 0.5 * self.retries if self.retries < 20 else 10
                _log.info("Link to proxy failed, retrying in {}".format(delay))
                async.DelayedCall(delay, self.node.network.join,
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
        _log.info("storage proxy up")
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
            kwargs = {}
            if 'key' in payload:
                kwargs['key'] = payload['key']
            if 'value' in payload:
                kwargs['value'] = payload['value']
            if 'response' in payload:
                kwargs['value'] = calvinresponse.CalvinResponse(encoded=payload['response'])
            self.replies.pop(payload['msg_uuid'])(**kwargs)

    def send(self, cmd, msg, cb):
        msg_id = calvinuuid.uuid("MSGID")
        if cb:
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

    def delete(self, key, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", {'key': key})
        self.send(cmd='DELETE',msg={'key':key}, cb=cb)

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

    def add_index(self, prefix, indexes, value, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", {'indexes': indexes, 'value': value})
        self.send(cmd='ADD_INDEX',msg={'prefix': prefix, 'index': indexes, 'value': value}, cb=cb)

    def remove_index(self, prefix, indexes, value, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", {'indexes': indexes, 'value': value})
        self.send(cmd='REMOVE_INDEX',msg={'prefix': prefix, 'index': indexes, 'value': value}, cb=cb)

    def get_index(self, prefix, index, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", {'index': index})
        self.send(cmd='GET_INDEX',msg={'prefix': prefix, 'index': index}, cb=cb)

    def bootstrap(self, addrs, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", None)

    def stop(self, cb=None):
        _log.analyze(self.node.id, "+ CLIENT", None)
        if cb:
            cb()
