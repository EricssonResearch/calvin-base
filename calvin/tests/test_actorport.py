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
from mock import Mock, call

from calvin.runtime.north.actormanager import ActorManager
from calvin.tests import DummyNode
from calvin.runtime.north.plugins.port.endpoint import LocalOutEndpoint, LocalInEndpoint
from calvin.actor.actorport import InPort, OutPort
from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.plugins.port.endpoint.common import Endpoint

pytestmark = pytest.mark.unittest


def create_actor(node):
    actor_manager = ActorManager(node)
    actor_id = actor_manager.new('std.Identity', {})
    actor = actor_manager.actors[actor_id]
    return actor


@pytest.fixture
def actor():
    return create_actor(DummyNode())


@pytest.fixture
def inport():
    return InPort("inport", actor())


@pytest.fixture
def outport():
    return OutPort("outport", actor())


def test_attach_endpoint_to_inport(inport, outport):
    inport.owner.did_connect = Mock()
    first_outport = OutPort("out", actor())
    first_endpoint = LocalInEndpoint(inport, first_outport)
    first_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    endpoint = LocalInEndpoint(inport, outport)
    endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing

    inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    inport.attach_endpoint(first_endpoint)
    assert inport.is_connected_to(first_outport.id)

    prev_endpoint = inport.attach_endpoint(endpoint)
    assert prev_endpoint == Endpoint.void()
    assert inport.is_connected_to(outport.id)
    assert inport.is_connected_to(first_outport.id)
    assert inport.owner.did_connect.called


def test_detach_endpoint_from_inport(inport, outport):
    endpoint = LocalInEndpoint(inport, outport)
    endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing

    inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    inport.attach_endpoint(endpoint)
    assert inport.is_connected_to(outport.id)
    inport.detach_endpoint(endpoint)
    assert not inport.is_connected_to(outport.id)


def test_attach_endpoint_to_outport(inport, outport):
    outport.owner.did_connect = Mock()
    first_inport = InPort("out", actor())
    first_endpoint = LocalOutEndpoint(outport, first_inport)
    first_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    endpoint = LocalOutEndpoint(outport, inport)
    endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing

    outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    outport.attach_endpoint(first_endpoint)
    assert outport.is_connected_to(first_endpoint.peer_id)

    outport.attach_endpoint(endpoint)
    assert outport.is_connected_to(endpoint.peer_id)
    assert outport.is_connected_to(first_endpoint.peer_id)
    assert outport.owner.did_connect.called


def test_detach_endpoint_from_outport(inport, outport):
    endpoint = LocalOutEndpoint(outport, inport)
    endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing

    outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    outport.attach_endpoint(endpoint)
    assert outport.is_connected_to(endpoint.peer_id)
    outport.detach_endpoint(endpoint)
    assert not outport.is_connected_to(endpoint.peer_id)


def test_disconnect_inport(inport, outport):
    inport.owner.did_disconnect = Mock()
    endpoint = LocalInEndpoint(inport, outport)
    endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing

    inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    inport.attach_endpoint(endpoint)
    assert inport.disconnect() == [endpoint]
    assert inport.owner.did_disconnect.called


def test_disconnect_outport(inport, outport):
    outport.owner.did_disconnect = Mock()
    outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    outport.queue.cancel = Mock()
    endpoint_1 = LocalOutEndpoint(outport, inport)
    endpoint_1._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    endpoint_2 = LocalOutEndpoint(outport, outport)
    endpoint_2._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing

    outport.attach_endpoint(endpoint_1)
    outport.attach_endpoint(endpoint_2)
    assert outport.disconnect() == [endpoint_1, endpoint_2]
    assert outport.owner.did_disconnect.called
    outport.queue.cancel.assert_has_calls([call(endpoint_1.peer_id), call(endpoint_2.peer_id)])


def test_inport_outport_connection(inport, outport):
    out_endpoint = LocalOutEndpoint(outport, inport)
    out_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    in_endpoint = LocalInEndpoint(inport, outport)
    in_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    outport.attach_endpoint(out_endpoint)
    inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    inport.attach_endpoint(in_endpoint)

    assert outport.tokens_available(1)
    assert outport.tokens_available(4)

    outport.write_token(1)
    assert outport.tokens_available(3)

    for e in outport.endpoints:
        e.communicate()
    assert inport.tokens_available(1)
    assert inport.peek_token() == 1
    inport.peek_cancel()

    assert inport.peek_token() == 1
    assert inport.tokens_available(0)


def test_set_outport_state(inport, outport):
    new_state = {
        'properties': {
            'routing': 'fanout',
            'nbr_peers': 2
        },
        'name': 'new_name',
        'id': '123',
        'queue': {
            'fifo': [{'value': 1} for n in range(5)],
            'N': 5,
            'readers': ['123'],
            'write_pos': 3,
            'read_pos': {'123': 2},
            'tentative_read_pos': {'123': 0},
            'queuetype': 'fifo'
        }
    }
    out_endpoint = LocalOutEndpoint(outport, inport)
    out_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    in_endpoint = LocalInEndpoint(inport, outport)
    in_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    inport.attach_endpoint(in_endpoint)
    outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    outport.attach_endpoint(out_endpoint)
    outport._set_state(new_state)

    assert outport.name == 'new_name'
    assert outport.id == '123'
    assert outport.properties['nbr_peers'] == 2

    assert outport.tokens_available(1)
    assert outport.tokens_available(3)
    outport.write_token(10)
    assert outport.queue.fifo[3] == 10


def test_set_inport_state(inport, outport):
    out_endpoint = LocalOutEndpoint(outport, inport)
    out_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    in_endpoint = LocalInEndpoint(inport, outport)
    in_endpoint._fifo_mismatch_fix = Mock() #  Skip fifo mismatch fixing
    outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    outport.attach_endpoint(out_endpoint)
    inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    inport.attach_endpoint(in_endpoint)

    new_state = {
        'name': 'new_name',
        'id': inport.id,
        'queue': {
            'fifo': [{'data': n} for n in range(5)],
            'N': 5,
            'readers': [in_endpoint.port.id],
            'write_pos': 5,
            'read_pos': {in_endpoint.port.id: 4},
            'tentative_read_pos': {in_endpoint.port.id: 2}
        }
    }
    inport._set_state(new_state)

    assert inport.name == 'new_name'
    assert inport.tokens_available(3)
    assert inport.peek_token().value == 2
    assert inport.peek_token().value == 3
    assert inport.peek_token().value == 4
    try:
        assert inport.peek_token()
        assert False
    except queue.common.QueueEmpty:
        assert True
    except:
        assert False
