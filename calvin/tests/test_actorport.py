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
from mock import Mock, call

from calvin.runtime.north.actormanager import ActorManager
from calvin.tests import DummyNode
from calvin.runtime.south.endpoint import LocalOutEndpoint, LocalInEndpoint
from calvin.actor.actorport import InPort, OutPort

pytestmark = pytest.mark.unittest


def create_actor(node):
    actor_manager = ActorManager(node)
    actor_id = actor_manager.new('std.Identity', {})
    actor = actor_manager.actors[actor_id]
    actor._calvinsys = Mock()
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
    old_inport = InPort("in", actor())
    old_endpoint = LocalInEndpoint(OutPort("out", actor()), old_inport)
    endpoint = LocalInEndpoint(outport, inport)

    inport.attach_endpoint(old_endpoint)
    assert inport.is_connected_to(old_inport.id)

    prev_endpoint = inport.attach_endpoint(endpoint)
    assert prev_endpoint == old_endpoint
    assert inport.is_connected_to(inport.id)
    assert not inport.is_connected_to(old_inport.id)
    assert inport.owner.did_connect.called


def test_detach_endpoint_from_inport(inport, outport):
    inport.owner.did_disconnect = Mock()
    endpoint = LocalInEndpoint(outport, inport)

    inport.attach_endpoint(endpoint)
    assert inport.is_connected_to(inport.id)
    inport.detach_endpoint(endpoint)
    assert not inport.is_connected_to(inport.id)
    assert inport.owner.did_disconnect.called


def test_attach_endpoint_to_outport(inport, outport):
    outport.owner.did_connect = Mock()
    old_endpoint = LocalOutEndpoint(OutPort("out", actor()), InPort("out", actor()))
    endpoint = LocalOutEndpoint(outport, inport)

    outport.attach_endpoint(old_endpoint)
    assert outport.is_connected_to(old_endpoint.peer_id)

    outport.attach_endpoint(endpoint)
    assert outport.is_connected_to(endpoint.peer_id)
    assert outport.is_connected_to(old_endpoint.peer_id)
    assert outport.owner.did_connect.called


def test_detach_endpoint_from_outport(inport, outport):
    outport.owner.did_disconnect = Mock()
    endpoint = LocalOutEndpoint(outport, inport)

    outport.attach_endpoint(endpoint)
    assert outport.is_connected_to(endpoint.peer_id)
    outport.detach_endpoint(endpoint)
    assert not outport.is_connected_to(endpoint.peer_id)
    assert outport.owner.did_disconnect.called


def test_disconnect_inport(inport, outport):
    inport.owner.did_disconnect = Mock()
    endpoint = LocalInEndpoint(outport, inport)

    inport.attach_endpoint(endpoint)
    assert inport.disconnect() == [endpoint]
    assert inport.owner.did_disconnect.called


def test_disconnect_outport(inport, outport):
    outport.owner.did_disconnect = Mock()
    outport.fifo.commit_reads = Mock()
    endpoint_1 = LocalOutEndpoint(outport, inport)
    endpoint_2 = LocalOutEndpoint(outport, outport)

    outport.attach_endpoint(endpoint_1)
    outport.attach_endpoint(endpoint_2)
    assert outport.disconnect() == [endpoint_1, endpoint_2]
    assert outport.owner.did_disconnect.called
    outport.fifo.commit_reads.assert_has_calls([call(endpoint_1.peer_id, False), call(endpoint_2.peer_id, False)])


def test_inport_outport_connection(inport, outport):
    out_endpoint = LocalOutEndpoint(outport, inport)
    in_endpoint = LocalInEndpoint(inport, outport)
    outport.attach_endpoint(out_endpoint)
    inport.attach_endpoint(in_endpoint)

    assert outport.can_write()
    assert outport.available_tokens() == 4

    outport.write_token(1)
    assert outport.available_tokens() == 3

    assert inport.available_tokens() == 1
    assert inport.peek_token() == 1
    inport.peek_rewind()

    assert inport.read_token() == 1
    assert inport.available_tokens() == 0


def test_set_outport_state(outport):
    new_state = {
        'fanout': 2,
        'name': 'new_name',
        'id': '123',
        'fifo': {
            'fifo': [{'value': 1} for n in range(5)],
            'N': 5,
            'readers': ['123'],
            'write_pos': 3,
            'read_pos': {'123': 2},
            'tentative_read_pos': {'123': 0}
        }
    }
    outport._set_state(new_state)

    assert outport.name == 'new_name'
    assert outport.id == '123'
    assert outport.fanout == 2

    assert outport.can_write()
    assert outport.available_tokens() == 3
    outport.write_token(10)
    assert outport.fifo.fifo[3] == 10


def test_set_inport_state(inport, outport):
    out_endpoint = LocalOutEndpoint(outport, inport)
    in_endpoint = LocalInEndpoint(inport, outport)
    outport.attach_endpoint(out_endpoint)
    inport.attach_endpoint(in_endpoint)

    new_state = {
        'name': 'new_name',
        'id': inport.id,
        'fifo': {
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
    assert inport.available_tokens() == 3
    assert inport.read_token().value == 2
    assert inport.read_token().value == 3
    assert inport.read_token().value == 4
    assert inport.read_token() is None
