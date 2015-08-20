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

from calvin.runtime.south.plugins.transports import base_transport
import calvin.runtime.north.plugins.coders.messages.message_coder_factory as coders


class FakeTransport(base_transport.BaseTransport):
    def __init__(self, rt_id, peer_id, uri, callbacks):
        super(FakeTransport, self).__init__(rt_id, peer_id, callbacks=callbacks)
        """docstring for __init__"""
        self.rt_id = rt_id
        self.peer_id = peer_id
        self.uri = uri
        self.peer = None

    def _set_peer(self, peer):
        self.peer = peer

    def get_coder(self):
        # But we actually cheat and never encode/decode
        return coders.get("json")

    def send(self, payload, timeout=None):
        self.peer._callback_execute('data_received', self.peer, payload)


class FakeTransportFactory(base_transport.BaseTransportFactory):
    def __init__(self, rt_id, callbacks):
        super(FakeTransportFactory, self).__init__(rt_id, callbacks=callbacks)
        self.peers = {}
        self.callbacks = callbacks

    def join(self, uri):
        """docstring for join"""
        _schema, peer_id = uri.split(':')
        if peer_id not in factories:
            raise Exception("FAKE trying to join not existing peer")
        tp = FakeTransport(self._rt_id, peer_id, uri, {'data_received': self.callbacks['data_received']})
        self.peers[peer_id] = tp
        ptp = factories[peer_id]._joined(self._rt_id, tp, "fake_transport:" + self._rt_id)
        tp._set_peer(ptp)

        # A none fake would likely call this after returned from call, hope that is not a problem
        self._callback_execute('join_finished', tp, peer_id, uri)

    def listen(self, uri):
        pass

    def _joined(self, peer_id, ptp, uri):
        tp = FakeTransport(self._rt_id, peer_id, uri, {'data_received': self.callbacks['data_received']})
        tp._set_peer(ptp)
        self._callback_execute('join_finished', tp, peer_id, uri)
        return tp

factories = {}


def register(id, callbacks, schemas, formats):
    if 'fake_transport' in schemas:
        f = FakeTransportFactory(id, callbacks)
        factories[id] = f
        return {'fake_transport': f}
    else:
        return {}
