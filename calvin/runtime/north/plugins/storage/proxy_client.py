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
from calvin.runtime.north.calvin_proto import RegistryTunnelProvider

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)


class ProxyRegistryClient(StorageBase):
    """
    Implements a storage that asks a master node, this is the client class
    args: node (for tunnel), host (master uri) 
    """
    def __init__(self, node, host):
        super(ProxyRegistryClient, self).__init__()
        self.tunnel_provider = RegistryTunnelProvider({'REPLY': self.reply_handler})
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
        

