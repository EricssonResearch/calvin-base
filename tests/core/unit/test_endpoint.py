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
from mock import Mock

from calvin.actor.actorport import InPort, OutPort
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.endpoint import LocalInEndpoint, LocalOutEndpoint, TunnelInEndpoint, TunnelOutEndpoint
from calvin.runtime.north.plugins.port import queue


@pytest.fixture
def port_cluster():
    class PortCluster:
        def __init__(self):        
            self.port = InPort("port", Mock())
            self.peer_port = OutPort("peer_port", Mock())
            self.local_in = LocalInEndpoint(self.port, self.peer_port)
            self.local_out = LocalOutEndpoint(self.peer_port, self.port)
            self.port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
            self.peer_port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
            self.peer_port.attach_endpoint(self.local_out)
            self.port.attach_endpoint(self.local_in)
    
    pc = PortCluster()
    return pc
    
@pytest.fixture
def tunnel_port_cluster():
    class TunnelPortCluster:
        def __init__(self):
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

    tpc = TunnelPortCluster()
    return tpc
    
    

# class TestLocalEndpoint():

    # def setUp(self):
    #     self.port = InPort("port", Mock())
    #     self.peer_port = OutPort("peer_port", Mock())
    #     self.local_in = LocalInEndpoint(self.port, self.peer_port)
    #     self.local_out = LocalOutEndpoint(self.peer_port, self.port)
    #     self.port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    #     self.peer_port.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    #     self.peer_port.attach_endpoint(self.local_out)
    #     self.port.attach_endpoint(self.local_in)

def test_is_connected(port_cluster):
    assert port_cluster.local_in.is_connected
    assert port_cluster.local_out.is_connected

def test_communicate(port_cluster):
    port_cluster.peer_port.queue.write(0, None)
    port_cluster.peer_port.queue.write(1, None)

    for e in port_cluster.peer_port.endpoints:
        e.communicate()

    assert port_cluster.peer_port.tokens_available(4)
    port_cluster.local_out.port.queue.write(2, None)
    assert not port_cluster.peer_port.tokens_available(4)
    assert port_cluster.peer_port.tokens_available(3)

    assert port_cluster.port.tokens_available(2, port_cluster.port.id)

    for e in port_cluster.peer_port.endpoints:
        e.communicate()

    assert port_cluster.port.tokens_available(3, port_cluster.port.id)
    for i in range(3):
        assert port_cluster.port.queue.peek(port_cluster.port.id) == i
    assert port_cluster.port.tokens_available(0, port_cluster.port.id)
    port_cluster.port.queue.commit(port_cluster.port.id)
    assert port_cluster.port.tokens_available(0, port_cluster.port.id)

def test_get_peer(port_cluster):
    assert port_cluster.local_in.get_peer() == ('local', port_cluster.peer_port.id)
    assert port_cluster.local_out.get_peer() == ('local', port_cluster.port.id)




def test_recv_token(tunnel_port_cluster):
    expected_reply = {
        'cmd': 'TOKEN_REPLY',
        'port_id': tunnel_port_cluster.port.id,
        'peer_port_id': tunnel_port_cluster.peer_port.id,
        'sequencenbr': 0,
        'value': 'ACK'
    }
    payload = {
        'port_id': tunnel_port_cluster.port.id,
        'peer_port_id': tunnel_port_cluster.peer_port.id,
        'sequencenbr': 0,
        'token': {'type': 'Token', 'data': 5}
    }
    tunnel_port_cluster.tunnel_in.recv_token(payload)
    assert tunnel_port_cluster.scheduler.tunnel_rx.called
    assert tunnel_port_cluster.port.queue.fifo[0].value == 5
    tunnel_port_cluster.tunnel.send.assert_called_with(expected_reply)

    tunnel_port_cluster.scheduler.reset_mock()
    tunnel_port_cluster.tunnel.send.reset_mock()

    payload['sequencenbr'] = 100
    tunnel_port_cluster.tunnel_in.recv_token(payload)
    assert not tunnel_port_cluster.scheduler.tunnel_rx.called
    expected_reply['sequencenbr'] = 100
    expected_reply['value'] = 'NACK'
    tunnel_port_cluster.tunnel.send.assert_called_with(expected_reply)

    tunnel_port_cluster.scheduler.reset_mock()
    tunnel_port_cluster.tunnel.send.reset_mock()

    payload['sequencenbr'] = 0
    tunnel_port_cluster.tunnel_in.recv_token(payload)
    assert not tunnel_port_cluster.scheduler.called
    expected_reply['sequencenbr'] = 0
    expected_reply['value'] = 'ACK'
    tunnel_port_cluster.tunnel.send.assert_called_with(expected_reply)

def test_get_peer(tunnel_port_cluster):
    assert tunnel_port_cluster.tunnel_in.get_peer() == (tunnel_port_cluster.peer_node_id, tunnel_port_cluster.peer_port.id)
    assert tunnel_port_cluster.tunnel_out.get_peer() == (tunnel_port_cluster.node_id, tunnel_port_cluster.port.id)

def test_reply(tunnel_port_cluster):
    tunnel_port_cluster.tunnel_out.port.queue.com_commit = Mock()
    tunnel_port_cluster.tunnel_out.port.queue.com_cancel = Mock()
    tunnel_port_cluster.tunnel.send = Mock()

    tunnel_port_cluster.tunnel_out.port.write_token(Token(1))
    tunnel_port_cluster.tunnel_out._send_one_token()
    nbr = tunnel_port_cluster.tunnel.send.call_args_list[-1][0][0]['sequencenbr']

    tunnel_port_cluster.tunnel_out.reply(0, 'ACK')
    tunnel_port_cluster.tunnel_out.port.queue.com_commit.assert_called_with(tunnel_port_cluster.port.id, nbr)
    assert tunnel_port_cluster.scheduler.tunnel_tx_ack.called

    tunnel_port_cluster.tunnel_out.port.write_token(Token(1))
    tunnel_port_cluster.tunnel_out._send_one_token()
    nbr = tunnel_port_cluster.tunnel.send.call_args_list[-1][0][0]['sequencenbr']

    tunnel_port_cluster.tunnel_out.reply(nbr, 'NACK')
    assert tunnel_port_cluster.tunnel_out.port.queue.com_cancel.called
    assert tunnel_port_cluster.scheduler.tunnel_tx_nack.called


def test_nack_reply(tunnel_port_cluster):
    tunnel_port_cluster.tunnel_out.port.write_token(Token(1))
    tunnel_port_cluster.tunnel_out._send_one_token()

    tunnel_port_cluster.tunnel_out.port.queue.commit(tunnel_port_cluster.port.id)
    assert tunnel_port_cluster.tunnel_out.port.queue.tentative_read_pos[tunnel_port_cluster.port.id] == 1
    assert tunnel_port_cluster.tunnel_out.port.queue.read_pos[tunnel_port_cluster.port.id] == 1

    tunnel_port_cluster.tunnel_out.port.write_token(Token(2))
    tunnel_port_cluster.tunnel_out.port.write_token(Token(3))
    tunnel_port_cluster.tunnel_out._send_one_token()
    tunnel_port_cluster.tunnel_out._send_one_token()

    assert tunnel_port_cluster.tunnel_out.port.queue.read_pos[tunnel_port_cluster.port.id] == 1
    assert tunnel_port_cluster.tunnel_out.port.queue.tentative_read_pos[tunnel_port_cluster.port.id] == 3

    tunnel_port_cluster.tunnel_out.reply(1, 'NACK')
    assert tunnel_port_cluster.tunnel_out.port.queue.tentative_read_pos[tunnel_port_cluster.port.id] == 1
    assert tunnel_port_cluster.tunnel_out.port.queue.read_pos[tunnel_port_cluster.port.id] == 1

def test_bulk_communicate(tunnel_port_cluster):
    tunnel_port_cluster.tunnel_out.port.write_token(Token(1))
    tunnel_port_cluster.tunnel_out.port.write_token(Token(2))
    tunnel_port_cluster.tunnel_out.bulk = True
    tunnel_port_cluster.tunnel_out.communicate()
    assert tunnel_port_cluster.tunnel.send.call_count == 2

def test_tunnel_communicate(tunnel_port_cluster):
    tunnel_port_cluster.tunnel_out.port.write_token(Token(1))
    tunnel_port_cluster.tunnel_out.port.write_token(Token(2))

    tunnel_port_cluster.tunnel_out.bulk = False

    assert tunnel_port_cluster.tunnel_out.communicate() is True
    assert tunnel_port_cluster.tunnel.send.call_count == 1

    assert tunnel_port_cluster.tunnel_out.communicate() is False

    tunnel_port_cluster.tunnel_out.reply(1, 'ACK')
    assert tunnel_port_cluster.tunnel_out.communicate() is True
    assert tunnel_port_cluster.tunnel.send.call_count == 2
