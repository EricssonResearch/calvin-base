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
from mock import Mock, patch

from calvin.runtime.north.actormanager import ActorManager
from calvin.runtime.north.plugins.port import queue
from calvin.common import calvinuuid

system_config_file = "actorstore.yaml"

@pytest.fixture()
def actor_manager(system_setup, dummy_node):
    """Return an ActorManager instance"""
    dummy_node.am = ActorManager(node=dummy_node)
    dummy_node.pm.remove_ports_of_actor = Mock(return_value = [])
    return dummy_node.am

def _new_actor(am, a_type, a_args, **kwargs):
    a_id = am.new(a_type, a_args, **kwargs)
    a = am.actors.get(a_id, None)
    assert a
    return a, a_id

def test_new_actor(actor_manager):
    # Test basic actor creation
    a_type = 'std.Constantify'
    constant = 42
    a, _ = _new_actor(actor_manager, a_type, {'constant':constant})
    assert a.constant, constant

def test_actor_state_get(actor_manager):
    # Test basic actor state retrieval
    a_type = 'std.Constantify'
    constant = 42
    a, a_id = _new_actor(actor_manager, a_type, {'constant':constant})
    s = a.serialize()

    assert s['managed']['constant'] == constant
    assert s['private']['_id'] == a_id

def test_new_actor_from_state(actor_manager):
    # Test basic actor state manipulation
    a_type = 'std.Constantify'
    constant = 42
    a, a_id = _new_actor(actor_manager, a_type, {'constant':constant})
    a.constant = 43
    s = a.serialize()
    actor_manager.destroy(a_id)
    assert len(actor_manager.actors) == 0

    b, b_id = _new_actor(actor_manager, a_type, None, state = s)

    assert a.constant == 43
    # Assert id is preserved
    assert a.id == a_id
    # Assert actor database is consistent
    assert actor_manager.actors[a_id]
    assert len(actor_manager.actors) == 1

@patch('calvin.runtime.north.storage.Storage.delete_actor')
def test_destroy_actor(delete_actor, actor_manager):
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42})
    actor_manager.destroy(actor_id)

    assert actor_id not in actor_manager.actors
    assert actor_manager.node.storage.delete_actor.call_args[0][0] == actor_id
    actor_manager.node.control.log_actor_destroy.assert_called_with(actor_id)

def test_enable_actor(actor_manager):
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42})

    actor.enable = Mock()
    actor_manager.enable(actor_id)
    assert actor.enable.called

def test_disable_actor(actor_manager):
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42})

    actor.disable = Mock()
    actor_manager.disable(actor_id)
    assert actor.disable.called

def test_migrate_to_same_node_does_nothing(actor_manager):
    callback_mock = Mock()
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42})
    actor.will_migrate = Mock()

    actor_manager.migrate(actor_id, actor_manager.node.id, callback_mock)
    assert not actor.will_migrate.called
    assert callback_mock.called
    args, kwargs = callback_mock.call_args
    assert kwargs['status'].status == 200

def test_migrate_non_existing_actor_returns_false(actor_manager):
    callback_mock = Mock()

    actor_manager.migrate("123", actor_manager.node.id, callback_mock)
    assert callback_mock.called
    args, kwargs = callback_mock.call_args
    assert kwargs['status'].status == 500

def test_migrate(actor_manager):
    callback_mock = Mock()

    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42})
    actor.outports['out'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    actor.inports['in'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
    peer_node = Mock()
    peer_node.id = calvinuuid.uuid("NODE")    
    assert peer_node != actor_manager.node

    actor.will_migrate = Mock()

    actor_manager.migrate(actor_id, peer_node.id, callback_mock)

    assert actor.will_migrate.called
    assert actor_manager.node.pm.disconnect.called

    args, kwargs = actor_manager.node.pm.disconnect.call_args
    assert kwargs['actor_id'] == actor_id

    cb = kwargs['callback']
    assert cb.kwargs['actor'] == actor
    assert cb.kwargs['actor_type'] == actor._type
    assert cb.kwargs['callback'] == callback_mock
    assert cb.kwargs['node_id'] == peer_node.id
    assert cb.kwargs['ports'] == actor.connections(actor_manager.node.id)
    actor_manager.node.control.log_actor_migrate.assert_called_once_with(actor_id, peer_node.id)

def test_connect(actor_manager):
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42})
    connection_list = [['1', '2', '3', '4'], ['5', '6', '7', '8']]
    callback_mock = Mock()

    actor_manager.connect(actor_id, connection_list, callback_mock)

    assert actor_manager.node.pm.connect.call_count == 2
    calls = actor_manager.node.pm.connect.call_args_list
    for index, (args, kwargs) in enumerate(calls):
        assert kwargs['port_id'] == connection_list[index][1]
        assert kwargs['peer_node_id'] == connection_list[index][2]
        assert kwargs['peer_port_id'] == connection_list[index][3]
        callback = kwargs['callback'].kwargs
        assert callback['peer_port_id'] == connection_list[index][3]
        assert callback['actor_id'] == actor_id
        assert callback['peer_port_ids'] == ['4', '8']
        assert callback['_callback'] == callback_mock

def test_connections_returns_actor_connections_for_current_node(actor_manager):
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42, 'name': 'actor'})
    actor.outports['out'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
    actor.inports['in'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))

    expected = {
        'actor_name': 'actor',
        'actor_id': actor_id,
        'inports': {actor.inports['in'].id: actor.inports['in'].get_peers()},
        'outports': {actor.outports['out'].id: actor.outports['out'].get_peers()}
    }
    assert actor_manager.connections(actor_id) == expected

def test_missing_actor(actor_manager):
    test_functions = [("report", ({},)), ("destroy", ()), ("enable", ()), ("disable", ()),
                      ("connect", ([], None)), ("connections", ()), ("dump", ()),
                      ("get_port_state", (None, ))]
    for func, args in test_functions:
        with pytest.raises(Exception) as excinfo:
            print(func)
            getattr(actor_manager, func)('123', *args)
        assert "Actor '123' not found" in str(excinfo.value)

def test_actor_type(actor_manager):
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42, 'name': 'actor'})
    assert actor_manager.actor_type(actor_id) == 'std.Constantify'

def test_actor_type_of_missing_actor(actor_manager):
    assert actor_manager.actor_type("123") == 'BAD ACTOR'

def test_enabled_actors(actor_manager):
    actor, actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42, 'name': 'actor'})
    enabled_actor, enabled_actor_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42, 'name': 'actor'})
    enabled_actor.enable()
    assert actor_manager.enabled_actors() == [enabled_actor]

def test_list_actors(actor_manager):
    actor_1, actor_1_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42, 'name': 'actor'})
    actor_2, actor_2_id = _new_actor(actor_manager, 'std.Constantify', {'constant': 42, 'name': 'actor'})
    actors = actor_manager.list_actors()
    assert actor_1_id in actors
    assert actor_2_id in actors

