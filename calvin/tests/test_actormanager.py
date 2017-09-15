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

import unittest
import pytest
from mock import Mock, patch

from calvin.tests import DummyNode
from calvin.runtime.north.actormanager import ActorManager
from calvin.runtime.north.plugins.port import queue

pytestmark = pytest.mark.unittest


class ActorManagerTests(unittest.TestCase):

    def setUp(self):
        n = DummyNode()
        self.am = ActorManager(node=n)
        n.am = self.am
        n.pm.remove_ports_of_actor = Mock(return_value = [])

    def tearDown(self):
        pass

    def _new_actor(self, a_type, a_args, **kwargs):
        a_id = self.am.new(a_type, a_args, **kwargs)
        a = self.am.actors.get(a_id, None)
        self.assertTrue(a)
        return a, a_id

    def test_new_actor(self):
        # Test basic actor creation
        a_type = 'std.Constant'
        data = 42
        a, _ = self._new_actor(a_type, {'data':data})
        self.assertEqual(a.data, data)

    def test_actor_state_get(self):
        # Test basic actor state retrieval
        a_type = 'std.Constant'
        data = 42
        a, a_id = self._new_actor(a_type, {'data':data})
        s = a.serialize()

        self.assertEqual(s['managed']['data'], data)
        self.assertEqual(s['private']['_id'], a_id)

    def test_new_actor_from_state(self):
        # Test basic actor state manipulation
        a_type = 'std.Constant'
        data = 42
        a, a_id = self._new_actor(a_type, {'data':data})
        a.data = 43
        s = a.serialize()
        self.am.destroy(a_id)
        self.assertEqual(len(self.am.actors), 0)

        b, b_id = self._new_actor(a_type, None, state = s)

        self.assertEqual(a.data, 43)
        # Assert id is preserved
        self.assertEqual(a.id, a_id)
        # Assert actor database is consistent
        self.assertTrue(self.am.actors[a_id])
        self.assertEqual(len(self.am.actors), 1)

    @patch('calvin.runtime.north.storage.Storage.delete_actor')
    @patch('calvin.runtime.north.metering.Metering.remove_actor_info')
    def test_destroy_actor(self, remove_actor_info, delete_actor):
        actor, actor_id = self._new_actor('std.Constant', {'data': 42})

        self.am.destroy(actor_id)

        assert actor_id not in self.am.actors
        remove_actor_info.assert_called_with(actor_id)
        assert self.am.node.storage.delete_actor.call_args[0][0] == actor_id
        self.am.node.control.log_actor_destroy.assert_called_with(actor_id)

    def test_enable_actor(self):
        actor, actor_id = self._new_actor('std.Constant', {'data': 42})

        actor.enable = Mock()
        self.am.enable(actor_id)
        assert actor.enable.called

    def test_disable_actor(self):
        actor, actor_id = self._new_actor('std.Constant', {'data': 42})

        actor.disable = Mock()
        self.am.disable(actor_id)
        assert actor.disable.called

    def test_migrate_to_same_node_does_nothing(self):
        callback_mock = Mock()
        actor, actor_id = self._new_actor('std.Constant', {'data': 42})
        actor.will_migrate = Mock()

        self.am.migrate(actor_id, self.am.node.id, callback_mock)
        assert not actor.will_migrate.called
        assert callback_mock.called
        args, kwargs = callback_mock.call_args
        self.assertEqual(kwargs['status'].status, 200)

    def test_migrate_non_existing_actor_returns_false(self):
        callback_mock = Mock()

        self.am.migrate("123", self.am.node.id, callback_mock)
        assert callback_mock.called
        args, kwargs = callback_mock.call_args
        self.assertEqual(kwargs['status'].status, 500)

    def test_migrate(self):
        callback_mock = Mock()

        actor, actor_id = self._new_actor('std.Constant', {'data': 42})
        actor.outports['token'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
        peer_node = DummyNode()

        actor.will_migrate = Mock()

        self.am.migrate(actor_id, peer_node.id, callback_mock)

        assert actor.will_migrate.called
        assert self.am.node.pm.disconnect.called

        args, kwargs = self.am.node.pm.disconnect.call_args
        self.assertEqual(kwargs['actor_id'], actor_id)

        cb = kwargs['callback']
        self.assertEqual(cb.kwargs['actor'], actor)
        self.assertEqual(cb.kwargs['actor_type'], actor._type)
        self.assertEqual(cb.kwargs['callback'], callback_mock)
        self.assertEqual(cb.kwargs['node_id'], peer_node.id)
        self.assertEqual(cb.kwargs['ports'], actor.connections(self.am.node.id))
        self.am.node.control.log_actor_migrate.assert_called_once_with(actor_id, peer_node.id)

    def test_connect(self):
        actor, actor_id = self._new_actor('std.Constant', {'data': 42})
        connection_list = [['1', '2', '3', '4'], ['5', '6', '7', '8']]
        callback_mock = Mock()

        self.am.connect(actor_id, connection_list, callback_mock)

        self.assertEqual(self.am.node.pm.connect.call_count, 2)
        calls = self.am.node.pm.connect.call_args_list
        for index, (args, kwargs) in enumerate(calls):
            self.assertEqual(kwargs['port_id'], connection_list[index][1])
            self.assertEqual(kwargs['peer_node_id'], connection_list[index][2])
            self.assertEqual(kwargs['peer_port_id'], connection_list[index][3])
            callback = kwargs['callback'].kwargs
            self.assertEqual(callback['peer_port_id'], connection_list[index][3])
            self.assertEqual(callback['actor_id'], actor_id)
            self.assertEqual(callback['peer_port_ids'], ['4', '8'])
            self.assertEqual(callback['_callback'], callback_mock)

    def test_connections_returns_actor_connections_for_current_node(self):
        actor, actor_id = self._new_actor('std.Constant', {'data': 42, 'name': 'actor'})
        actor.outports['token'].set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
        expected = {
            'actor_name': 'actor',
            'actor_id': actor_id,
            'inports': {},
            'outports': {actor.outports['token'].id: actor.outports['token'].get_peers()}
        }
        self.assertEqual(self.am.connections(actor_id), expected)

    def test_missing_actor(self):
        test_functions = [("report", ({},)), ("destroy", ()), ("enable", ()), ("disable", ()),
                          ("connect", ([], None)), ("connections", ()), ("dump", ()),
                          ("get_port_state", (None, ))]
        for func, args in test_functions:
            with pytest.raises(Exception) as excinfo:
                print func
                getattr(self.am, func)('123', *args)
            assert "Actor '123' not found" in str(excinfo.value)

    def test_actor_type(self):
        actor, actor_id = self._new_actor('std.Constant', {'data': 42, 'name': 'actor'})
        self.assertEqual(self.am.actor_type(actor_id), 'std.Constant')

    def test_actor_type_of_missing_actor(self):
        self.assertEqual(self.am.actor_type("123"), 'BAD ACTOR')

    def test_enabled_actors(self):
        actor, actor_id = self._new_actor('std.Constant', {'data': 42, 'name': 'actor'})
        enabled_actor, enabled_actor_id = self._new_actor('std.Constant', {'data': 42, 'name': 'actor'})
        enabled_actor.enable()
        self.assertEqual(self.am.enabled_actors(), [enabled_actor])

    def test_list_actors(self):
        actor_1, actor_1_id = self._new_actor('std.Constant', {'data': 42, 'name': 'actor'})
        actor_2, actor_2_id = self._new_actor('std.Constant', {'data': 42, 'name': 'actor'})
        actors = self.am.list_actors()
        assert actor_1_id in actors
        assert actor_2_id in actors


if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(ActorManagerTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
