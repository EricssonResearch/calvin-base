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
from calvin.tests import DummyNode, TestPort
from calvin.runtime.north.actormanager import ActorManager
from calvin.runtime.north.plugins.port.endpoint import LocalOutEndpoint, LocalInEndpoint
from calvin.actor.actor import Actor
from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.calvinsys import get_calvinsys

pytestmark = pytest.mark.unittest


def create_actor(node):
    actor_manager = ActorManager(node)
    actor_id = actor_manager.new('std.Identity', {})
    actor = actor_manager.actors[actor_id]
    actor.inports['token'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    actor.inports['token'].queue.add_reader(actor.inports['token'].id, {})
    actor.outports['token'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    return actor


@pytest.fixture
def actor():
    get_calvinsys()._node = Mock()
    return create_actor(DummyNode())


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
    else:
        assert not actor.fsm.transition_to.called


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
    actor.fsm.state = Mock(return_value=Actor.STATUS.READY)
    actor.did_disconnect(None)
    if expected:
        actor.fsm.transition_to.assert_called_with(Actor.STATUS.READY)
    else:
        assert not (actor.fsm.transition_to.called and Actor.STATUS.READY in actor.fsm.transition_to.call_args[0])


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

    in_peer_port = TestPort("x", "out")
    out_peer_port = TestPort("y", "in")
    out_peer_port.queue.add_reader(out_peer_port.id, {})
    in_peer_port.queue.add_reader(inport.id, {})

    inport.attach_endpoint(LocalInEndpoint(inport, in_peer_port))
    outport.attach_endpoint(LocalOutEndpoint(outport, out_peer_port))

    assert actor.connections(node) == {
        'actor_id': actor.id,
        'actor_name': actor.name,
        'inports': {inport.id: [(node, in_peer_port.id)]},
        'outports': {outport.id: [(node, out_peer_port.id)]}
    }


def test_state(actor):
    inport = actor.inports['token']
    outport = actor.outports['token']
    correct_state = {
        'custom': {},
        'managed': {'dump': False, 'last': None},
        'security': {'_subject_attributes': None},
        'private': {
        '_component_members': [actor.id],
        '_has_started': False,
        '_deployment_requirements': [],
        '_signature': None,
        '_id': actor.id,
        '_port_property_capabilities': None,
        '_migration_info': None,
        '_replication_id': {},
        'inports': {'token': {'properties': {'direction': 'in',
                                             'routing': 'default',
                                             'nbr_peers': 1},
                              'queue': {'N': 5,
                                       'fifo': [{'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'},
                                                {'data': 0, 'type': 'Token'}],
                                       'queuetype': 'fanout_fifo',
                                       'read_pos': {inport.id: 0},
                                       'reader_offset': {inport.id: 0},
                                       'readers': [inport.id],
                                       'tentative_read_pos': {inport.id: 0},
                                       'write_pos': 0},
                              'id': inport.id,
                              'name': 'token'}},
        '_name': '',
        'outports': {'token': {'properties': {'direction': 'out',
                                              'routing': 'fanout',
                                              'nbr_peers': 1},
                               'queue': {'N': 5,
                                        'fifo': [{'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'},
                                                 {'data': 0, 'type': 'Token'}],
                                        'queuetype': 'fanout_fifo',
                                        'read_pos': {},
                                        'reader_offset': {},
                                        'readers': [],
                                        'tentative_read_pos': {},
                                        'write_pos': 0},
                               'id': outport.id,
                               'name': 'token'}}
                           },
                         }

    test_state = actor.serialize()
    for prop, expected in correct_state.iteritems():
        actual = test_state[prop]
        for k, v in expected.iteritems():
            # Read state use list to support JSON serialization
            if isinstance(v, set):
                assert set(actual[k]) == v
            else:
                assert actual[k] == v

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
    assert actor.requirements_get()[:-1] == []
    assert actor.requirements_get()[-1]['op'] == 'port_property_match'
    actor.requirements_add([1, 2, 3])
    assert actor.requirements_get()[:-1] == [1, 2, 3]
    assert actor.requirements_get()[-1]['op'] == 'port_property_match'
    actor.requirements_add([4, 5])
    assert actor.requirements_get()[:-1] == [4, 5]
    assert actor.requirements_get()[-1]['op'] == 'port_property_match'
    actor.requirements_add([6, 7], extend=True)
    assert actor.requirements_get()[:-1] == [4, 5, 6, 7]
    assert actor.requirements_get()[-1]['op'] == 'port_property_match'
