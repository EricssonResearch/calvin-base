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

import pytest

from mock import Mock
from calvin.tests import DummyNode
from calvin.runtime.north.actormanager import ActorManager
from calvin.runtime.south.endpoint import LocalOutEndpoint, LocalInEndpoint
from calvin.actor.actor import Actor

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


@pytest.mark.parametrize("port_type,port_name,port_property,value,expected", [
    ("invalid", "", "", "", False),
    ("in", "missing", "", "", False),
    ("out", "missing", "", "", False),
    ("out", "token", "missing", "", False),
    ("in", "token", "missing", "", False),
    ("out", "token", "name", "new_name", True),
    ("out", "token", "name", "new_name", True),
])
def test_set_port_property(port_type, port_name, port_property, value, expected):
    assert actor().set_port_property(port_type, port_name, port_property, value) is expected


@pytest.mark.parametrize("inport_ret_val,outport_ret_val,expected", [
    (False, False, False),
    (False, True, False),
    (True, False, False),
    (True, True, True),
])
def test_did_connect(actor, inport_ret_val, outport_ret_val, expected):
    for port in actor.inports.values():
        port.is_connected = Mock(return_value=inport_ret_val)
    for port in actor.outports.values():
        port.is_connected = Mock(return_value=outport_ret_val)

    actor.fsm = Mock()
    actor.did_connect(None)
    if expected:
        actor.fsm.transition_to.assert_called_with(Actor.STATUS.ENABLED)
        assert actor._calvinsys.scheduler_wakeup.called
    else:
        assert not actor.fsm.transition_to.called
        assert not actor._calvinsys.scheduler_wakeup.called


@pytest.mark.parametrize("inport_ret_val,outport_ret_val,expected", [
    (True, True, False),
    (True, False, False),
    (False, True, False),
    (False, False, True),
])
def test_did_disconnect(actor, inport_ret_val, outport_ret_val, expected):
    for port in actor.inports.values():
        port.is_connected = Mock(return_value=inport_ret_val)
    for port in actor.outports.values():
        port.is_connected = Mock(return_value=outport_ret_val)

    actor.fsm = Mock()
    actor.did_disconnect(None)
    if expected:
        actor.fsm.transition_to.assert_called_with(Actor.STATUS.READY)
    else:
        assert not actor.fsm.transition_to.called


def test_enabled(actor):
    actor.enable()
    assert actor.enabled()
    actor.disable()
    assert not actor.enabled()


def test_connections():
    node = DummyNode()
    node.id = "node_id"
    actor = create_actor(node)
    inport = actor.inports['token']
    outport = actor.outports['token']

    port = Mock()
    port.id = "x"
    peer_port = Mock()
    peer_port.id = "y"

    inport.attach_endpoint(LocalInEndpoint(port, peer_port))
    outport.attach_endpoint(LocalOutEndpoint(port, peer_port))

    assert actor.connections(node) == {
        'actor_id': actor.id,
        'actor_name': actor.name,
        'inports': {inport.id: (node, "y")},
        'outports': {outport.id: [(node, "y")]}
    }


def test_state(actor):
    inport = actor.inports['token']
    outport = actor.outports['token']
    correct_state = {
        '_component_members': set([actor.id]),
        '_deployment_requirements': [],
        '_managed': set(['dump', '_signature', 'id', '_deployment_requirements', 'name', 'credentials']),
        '_signature': None,
        'dump': False,
        'id': actor.id,
        'inports': {'token': {'fifo': {'N': 5,
                                       'fifo': [{'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'}],
                                       'read_pos': {inport.id: 0},
                                       'readers': [inport.id],
                                       'tentative_read_pos': {inport.id: 0},
                                       'write_pos': 0},
                              'id': inport.id,
                              'name': 'token'}},
        'name': '',
        'outports': {'token': {'fanout': 1,
                               'fifo': {'N': 5,
                                        'fifo': [{'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'}],
                                        'read_pos': {},
                                        'readers': [],
                                        'tentative_read_pos': {},
                                        'write_pos': 0},
                               'id': outport.id,
                               'name': 'token'}}}
    test_state = actor.state()
    for k, v in correct_state.iteritems():
        # Read state use list to support JSON serialization
        if isinstance(v, set):
            assert set(test_state[k]) == v
        else:
            assert test_state[k] == v

@pytest.mark.parametrize("prev_signature,new_signature,expected", [
    (None, "new_val", "new_val"),
    ("old_val", "new_val", "old_val")
])
def test_set_signature(actor, prev_signature, new_signature, expected):
    actor.signature_set(prev_signature)
    actor.signature_set(new_signature)
    assert actor._signature == expected


def test_component(actor):
    actor.component_add(1)
    assert 1 in actor.component_members()

    actor.component_add([2, 3])
    assert 2 in actor.component_members()
    assert 3 in actor.component_members()

    actor.component_remove(1)
    assert 1 not in actor.component_members()
    actor.component_remove([2, 3])
    assert 2 not in actor.component_members()
    assert 3 not in actor.component_members()


def test_requirements(actor):
    assert actor.requirements_get() == []
    actor.requirements_add([1, 2, 3])
    assert actor.requirements_get() == [1, 2, 3]
    actor.requirements_add([4, 5])
    assert actor.requirements_get() == [4, 5]
    actor.requirements_add([6, 7], extend=True)
    assert actor.requirements_get() == [4, 5, 6, 7]
