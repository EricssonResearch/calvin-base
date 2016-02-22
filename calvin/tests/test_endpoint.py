# -*- coding: utf-8 -*-

# Copyright (c) 2016 Philip Ståhl
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
from calvin.runtime.south.endpoint import LocalInEndpoint, LocalOutEndpoint, TunnelInEndpoint, TunnelOutEndpoint

pytestmark = pytest.mark.unittest


class TestLocalEndpoint(unittest.TestCase):

    def setUp(self):
        self.port = InPort("port", Mock())
        self.peer_port = OutPort("peer_port", Mock())
        self.local_in = LocalInEndpoint(self.port, self.peer_port)
        self.local_out = LocalOutEndpoint(self.peer_port, self.port)
        self.port.attach_endpoint(self.local_in)
        self.peer_port.attach_endpoint(self.local_out)

    def test_is_connected(self):
        assert self.local_in.is_connected
        assert self.local_out.is_connected

    def test_read_token_fixes_fifo_mismatch(self):
        self.local_in.fifo_mismatch = True
        token = self.local_in.read_token()
        assert token is None
        assert self.local_in.fifo_mismatch is False

    def test_read_token_commits_if_token_is_not_none(self):
        self.local_in.port.fifo.commit_reads = Mock()
        self.local_out.port.fifo.commit_reads = Mock()
        self.local_in.port.fifo.write(1)

        assert self.local_in.data_in_local_fifo is True
        assert self.local_in.read_token() == 1
        assert self.local_in.data_in_local_fifo is True
        self.local_in.port.fifo.commit_reads.assert_called_with(self.port.id, True)

        self.local_out.port.fifo.write(2)

        assert self.local_in.data_in_local_fifo is True
        assert self.local_in.read_token() == 2
        assert self.local_in.data_in_local_fifo is False
        self.local_out.port.fifo.commit_reads.assert_called_with(self.port.id, True)

    def test_peek_token(self):
        self.local_in.port.fifo.commit_reads = Mock()
        self.local_out.port.fifo.commit_reads = Mock()
        self.local_in.port.fifo.write(1)

        assert self.local_in.peek_token() == 1
        assert not self.local_in.port.fifo.commit_reads.called
        assert self.local_in.peek_token() is None
        self.local_in.peek_rewind()
        self.local_in.commit_peek_as_read()
        self.local_in.port.fifo.commit_reads.assert_called_with(self.port.id)
        self.local_out.port.fifo.commit_reads.assert_called_with(self.port.id)

        self.local_in.port.fifo.commit_reads.reset_mock()
        self.local_out.port.fifo.commit_reads.reset_mock()

        self.local_out.port.fifo.write(2)
        assert self.local_in.peek_token() == 2
        assert not self.local_out.port.fifo.commit_reads.called
        self.local_in.commit_peek_as_read()
        assert not self.local_in.port.fifo.commit_reads.called
        self.local_out.port.fifo.commit_reads.assert_called_with(self.port.id)

    def test_available_tokens(self):
        self.local_in.port.fifo.write(1)
        self.local_in.port.fifo.write(1)
        assert self.local_in.available_tokens() == 2
        self.local_out.port.fifo.write(1)
        assert self.local_in.available_tokens() == 3

    def test_get_peer(self):
        assert self.local_in.get_peer() == ('local', self.peer_port.id)
        assert self.local_out.get_peer() == ('local', self.port.id)


class TestTunnelEndpoint(unittest.TestCase):

    def setUp(self):
        self.port = InPort("port", Mock())
        self.peer_port = OutPort("peer_port", Mock())
        self.tunnel = Mock()
        self.trigger_loop = Mock()
        self.node_id = 123
        self.peer_node_id = 456
        self.tunnel_in = TunnelInEndpoint(self.port, self.tunnel, self.peer_node_id, self.peer_port.id, self.trigger_loop)
        self.tunnel_out = TunnelOutEndpoint(self.peer_port, self.tunnel, self.node_id, self.port.id, self.trigger_loop)
        self.port.attach_endpoint(self.tunnel_in)
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
        assert self.trigger_loop.called
        assert self.port.fifo.fifo[0].value == 5
        self.tunnel.send.assert_called_with(expected_reply)

        self.trigger_loop.reset_mock()
        self.tunnel.send.reset_mock()

        payload['sequencenbr'] = 100
        self.tunnel_in.recv_token(payload)
        assert not self.trigger_loop.called
        expected_reply['sequencenbr'] = 100
        expected_reply['value'] = 'NACK'
        self.tunnel.send.assert_called_with(expected_reply)

        self.trigger_loop.reset_mock()
        self.tunnel.send.reset_mock()

        payload['sequencenbr'] = 0
        self.tunnel_in.recv_token(payload)
        assert not self.trigger_loop.called
        expected_reply['sequencenbr'] = 0
        expected_reply['value'] = 'ACK'
        self.tunnel.send.assert_called_with(expected_reply)

    def test_read_token(self):
        self.tunnel_in.port.fifo.write(4)
        self.tunnel_in.port.fifo.commit_reads = Mock()
        assert self.tunnel_in.read_token() == 4
        self.tunnel_in.port.fifo.commit_reads.assert_called_with(self.port.id, True)

    def test_peek_token(self):
        self.tunnel_in.port.fifo.write(4)
        assert self.tunnel_in.peek_token() == 4
        assert self.tunnel_in.read_token() is None
        self.tunnel_in.peek_rewind()
        assert self.tunnel_in.read_token() == 4

    def test_available_tokens(self):
        self.tunnel_in.port.fifo.write(4)
        self.tunnel_in.port.fifo.write(5)
        assert self.tunnel_in.available_tokens() == 2

    def test_get_peer(self):
        assert self.tunnel_in.get_peer() == (self.peer_node_id, self.peer_port.id)
        assert self.tunnel_out.get_peer() == (self.node_id, self.port.id)

    def test_reply(self):
        self.tunnel_out.port.fifo.commit_one_read = Mock()

        self.tunnel_out.port.write_token(Token(1))
        self.tunnel_out._send_one_token()

        self.tunnel_out.reply(0, 'ACK')
        self.tunnel_out.port.fifo.commit_one_read.assert_called_with(self.port.id, True)
        assert self.trigger_loop.called

        self.tunnel_out.port.fifo.commit_one_read.reset_mock()
        self.tunnel_out.reply(1, 'NACK')
        assert not self.tunnel_out.port.fifo.commit_one_read.called

    def test_nack_reply(self):
        self.tunnel_out.port.write_token(Token(1))
        self.tunnel_out._send_one_token()

        self.tunnel_out.port.fifo.commit_reads(self.port.id, True)
        assert self.tunnel_out.port.fifo.tentative_read_pos[self.port.id] == 1
        assert self.tunnel_out.port.fifo.read_pos[self.port.id] == 1

        self.tunnel_out.port.write_token(Token(2))
        self.tunnel_out.port.write_token(Token(3))
        self.tunnel_out._send_one_token()
        self.tunnel_out._send_one_token()

        assert self.tunnel_out.port.fifo.read_pos[self.port.id] == 1
        assert self.tunnel_out.port.fifo.tentative_read_pos[self.port.id] == 3

        self.tunnel_out.reply(1, 'NACK')
        assert self.tunnel_out.port.fifo.tentative_read_pos[self.port.id] == 1
        assert self.tunnel_out.port.fifo.read_pos[self.port.id] == 1

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
