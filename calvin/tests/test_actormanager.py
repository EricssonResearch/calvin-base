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
import mock
from calvin.runtime.north.actormanager import ActorManager
from calvin.runtime.north import metering


class DummyNode:

    def __init__(self):
        self.id = id(self)
        self.pm = mock.Mock()
        self.storage = mock.Mock()
        self.control = mock.Mock()
        self.metering = metering.set_metering(metering.Metering(self))

    def calvinsys(self):
        return None


class ActorManagerTests(unittest.TestCase):

    def setUp(self):
        n = DummyNode()
        self.am = ActorManager(node=n)
        n.am = self.am

    def tearDown(self):
        pass

    def _new_actor(self, a_type, a_args, **kwargs):
        a_id = self.am.new(a_type, a_args, **kwargs)
        a = self.am.actors.get(a_id, None)
        self.assertTrue(a)
        return a, a_id

    def testNewActor(self):
        # Test basic actor creation
        a_type = 'std.Constant'
        data = 42
        a, _ = self._new_actor(a_type, {'data':data})
        self.assertEqual(a.data, data)

    def testActorStateGet(self):
        # Test basic actor state retrieval
        a_type = 'std.Constant'
        data = 42
        a, a_id = self._new_actor(a_type, {'data':data})
        s = a.state()

        self.assertEqual(s['data'], data)
        self.assertEqual(s['id'], a_id)
        self.assertEqual(s['n'], 1)


    def testNewActorFromState(self):
        # Test basic actor state manipulation
        a_type = 'std.Constant'
        data = 42
        a, a_id = self._new_actor(a_type, {'data':data})
        a.data = 43
        a.n = 2
        s = a.state()
        self.am.destroy(a_id)
        self.assertEqual(len(self.am.actors), 0)

        b, b_id = self._new_actor(a_type, None, state = s)

        self.assertEqual(a.data, 43)
        self.assertEqual(a.n, 2)
        # Assert id is preserved
        self.assertEqual(a.id, a_id)
        # Assert actor database is consistent
        self.assertTrue(self.am.actors[a_id])
        self.assertEqual(len(self.am.actors), 1)



if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(ActorManagerTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
