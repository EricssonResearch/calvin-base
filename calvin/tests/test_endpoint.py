# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2018 Ericsson AB
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

import pytest
import unittest
from mock import Mock

from calvin.actor.actorport import InPort, OutPort
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.endpoint import LocalInEndpoint, LocalOutEndpoint, TunnelInEndpoint, TunnelOutEndpoint
from calvin.runtime.north.plugins.port import queue

pytestmark = pytest.mark.unittest


class TestLocalEndpoint(unittest.TestCase):

    def setUp(self):
        self.port = InPort("port", Mock())
        self.peer_port = OutPort("peer_port", Mock())
        self.local_in = LocalInEndpoint(self.port, self.peer_port)
        self.local_out = LocalOutEndpoint(self.peer_port, self.port)
        self.port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
        self.peer_port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
        self.peer_port.attach_endpoint(self.local_out)
        self.port.attach_endpoint(self.local_in)

    def test_is_connected(self):
        assert self.local_in.is_connected
        assert self.local_out.is_connected

    def test_communicate(self):
        self.peer_port.queue.write(0, None)
        self.peer_port.queue.write(1, None)

        for e in self.peer_port.endpoints:
            e.communicate()

        assert self.peer_port.tokens_available(4)
        self.local_out.port.queue.write(2, None)
        assert not self.peer_port.tokens_available(4)
        assert self.peer_port.tokens_available(3)

        assert self.port.tokens_available(2, self.port.id)

        for e in self.peer_port.endpoints:
            e.communicate()

        assert self.port.tokens_available(3, self.port.id)
        for i in range(3):
            assert self.port.queue.peek(self.port.id) == i
        assert self.port.tokens_available(0, self.port.id)
        self.port.queue.commit(self.port.id)
        assert self.port.tokens_available(0, self.port.id)

    def test_get_peer(self):
        assert self.local_in.get_peer() == ('local', self.peer_port.id)
        assert self.local_out.get_peer() == ('local', self.port.id)


class TestTunnelEndpoint(unittest.TestCase):

    def setUp(self):
        self.port = InPort("port", Mock())
        self.peer_port = OutPort("peer_port", Mock())
        self.tunnel = Mock()
        self.scheduler = Mock()
        self.node_id = 123
        self.peer_node_id = 456
        self.tunnel_in = TunnelInEndpoint(self.port, self.tunnel, self.peer_node_id, self.peer_port.id, {}, self.scheduler)
        self.tunnel_out = TunnelOutEndpoint(self.peer_port, self.tunnel, self.node_id, self.port.id, {}, self.scheduler)
        self.port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
        self.port.attach_endpoint(self.tunnel_in)
        self.peer_port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
        self.peer_port.attach_endpoint(self.tunnel_out)

    def test_recv_token(self):
        expected_reply = {
            'cmd': 'TOKEN_REPLY',
            'port_id': self.port.id,
            'peer_port_id': self.peer_port.id,
            'sequencenbr': 0,
            'value': 'ACK'
        }
        payload = {
            'port_id': self.port.id,
            'peer_port_id': self.peer_port.id,
            'sequencenbr': 0,
            'token': {'type': 'Token', 'data': 5}
        }
        self.tunnel_in.recv_token(payload)
        assert self.scheduler.tunnel_rx.called
        assert self.port.queue.fifo[0].value == 5
        self.tunnel.send.assert_called_with(expected_reply)

        self.scheduler.reset_mock()
        self.tunnel.send.reset_mock()

        payload['sequencenbr'] = 100
        self.tunnel_in.recv_token(payload)
        assert not self.scheduler.tunnel_rx.called
        expected_reply['sequencenbr'] = 100
        expected_reply['value'] = 'NACK'
        self.tunnel.send.assert_called_with(expected_reply)

        self.scheduler.reset_mock()
        self.tunnel.send.reset_mock()

        payload['sequencenbr'] = 0
        self.tunnel_in.recv_token(payload)
        assert not self.scheduler.called
        expected_reply['sequencenbr'] = 0
        expected_reply['value'] = 'ACK'
        self.tunnel.send.assert_called_with(expected_reply)

    def test_get_peer(self):
        assert self.tunnel_in.get_peer() == (self.peer_node_id, self.peer_port.id)
        assert self.tunnel_out.get_peer() == (self.node_id, self.port.id)

    def test_reply(self):
        self.tunnel_out.port.queue.com_commit = Mock()
        self.tunnel_out.port.queue.com_cancel = Mock()
        self.tunnel.send = Mock()

        self.tunnel_out.port.write_token(Token(1))
        self.tunnel_out._send_one_token()
        nbr = self.tunnel.send.call_args_list[-1][0][0]['sequencenbr']

        self.tunnel_out.reply(0, 'ACK')
        self.tunnel_out.port.queue.com_commit.assert_called_with(self.port.id, nbr)
        assert self.scheduler.tunnel_tx_ack.called

        self.tunnel_out.port.write_token(Token(1))
        self.tunnel_out._send_one_token()
        nbr = self.tunnel.send.call_args_list[-1][0][0]['sequencenbr']

        self.tunnel_out.reply(nbr, 'NACK')
        assert self.tunnel_out.port.queue.com_cancel.called
        assert self.scheduler.tunnel_tx_nack.called


    def test_nack_reply(self):
        self.tunnel_out.port.write_token(Token(1))
        self.tunnel_out._send_one_token()

        self.tunnel_out.port.queue.commit(self.port.id)
        assert self.tunnel_out.port.queue.tentative_read_pos[self.port.id] == 1
        assert self.tunnel_out.port.queue.read_pos[self.port.id] == 1

        self.tunnel_out.port.write_token(Token(2))
        self.tunnel_out.port.write_token(Token(3))
        self.tunnel_out._send_one_token()
        self.tunnel_out._send_one_token()

        assert self.tunnel_out.port.queue.read_pos[self.port.id] == 1
        assert self.tunnel_out.port.queue.tentative_read_pos[self.port.id] == 3

        self.tunnel_out.reply(1, 'NACK')
        assert self.tunnel_out.port.queue.tentative_read_pos[self.port.id] == 1
        assert self.tunnel_out.port.queue.read_pos[self.port.id] == 1

    def test_bulk_communicate(self):
        self.tunnel_out.port.write_token(Token(1))
        self.tunnel_out.port.write_token(Token(2))
        self.tunnel_out.bulk = True
        self.tunnel_out.communicate()
        assert self.tunnel.send.call_count == 2

    def test_communicate(self):
        self.tunnel_out.port.write_token(Token(1))
        self.tunnel_out.port.write_token(Token(2))

        self.tunnel_out.bulk = False

        assert self.tunnel_out.communicate() is True
        assert self.tunnel.send.call_count == 1

        assert self.tunnel_out.communicate() is False

        self.tunnel_out.reply(1, 'ACK')
        assert self.tunnel_out.communicate() is True
        assert self.tunnel.send.call_count == 2
