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
import time
import multiprocessing
from calvin.runtime.north import calvin_node
from calvin.Tools import cscompiler as compiler
from calvin.Tools import deployer
import pytest
from calvin.utilities import utils
from calvin.utilities.nodecontrol import dispatch_node
from calvin.utilities import calvinuuid
from warnings import warn
from calvin.utilities.attribute_resolver import format_index_string

def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)

class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.rt1 = dispatch_node("calvinip://localhost:5000", "http://localhost:5003")
        self.rt2 = dispatch_node("calvinip://localhost:5001", "http://localhost:5004")
        self.rt3 = dispatch_node("calvinip://localhost:5002", "http://localhost:5005")
        utils.peer_setup(self.rt1, ["calvinip://localhost:5001", "calvinip://localhost:5002"])
        utils.peer_setup(self.rt2, ["calvinip://localhost:5000", "calvinip://localhost:5002"])
        utils.peer_setup(self.rt3, ["calvinip://localhost:5000", "calvinip://localhost:5001"])

    def tearDown(self):
        utils.quit(self.rt1)
        utils.quit(self.rt2)
        utils.quit(self.rt3)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        time.sleep(0.2)

    def assert_lists_equal(self, expected, actual, min_length=5):
        self.assertTrue(len(actual) >= min_length, "Received data too short (%d), need at least %d" % (len(actual), min_length))
        l = min([len(expected), len(actual)])
        self.assertListEqual(expected[:l], actual[:l])

@pytest.mark.slow
class TestIndex(CalvinTestBase):

    @pytest.mark.slow
    def testLocalIndex(self):
        # We don't have a way of preventing DHT storage from starting,
        # but if this test is run first the storage is not yet up and running
        lindex = {}
        lindex['Harald'] = [calvinuuid.uuid("NODE") for i in range(1,5)]
        lindex['Per'] = [calvinuuid.uuid("NODE") for i in range(1,5)]
        common = calvinuuid.uuid("NODE")

        for n, node_ids in lindex.items():
            for id_ in node_ids:
                #print "ADD", n, id_
                utils.add_index(self.rt1, "node/affiliation/owner/com.ericsson/" + n, id_)

        h_ = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Harald")
        h = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson")

        assert(h_['result'] is None)  # Test that the storage is local
        assert(set(h['result']) == set(lindex["Harald"]))
        assert(set(p['result']) == set(lindex["Per"]))
        assert(set(e['result']) == set(lindex["Per"] + lindex["Harald"]))

        for n, node_ids in lindex.items():
            utils.remove_index(self.rt1, "node/affiliation/owner/com.ericsson/" + n, node_ids[0])

        h = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson")

        assert(set(h['result']) == set(lindex["Harald"][1:]))
        assert(set(p['result']) == set(lindex["Per"][1:]))
        assert(set(e['result']) == set(lindex["Per"][1:] + lindex["Harald"][1:]))

        utils.add_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald", common)
        utils.add_index(self.rt1, "node/affiliation/owner/com.ericsson/Per", common)

        h = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson")

        assert(set(h['result']) == set(lindex["Harald"][1:] + [common]))
        assert(set(p['result']) == set(lindex["Per"][1:] + [common]))
        assert(set(e['result']) == set(lindex["Per"][1:] + lindex["Harald"][1:] + [common]))

        for node_id in lindex['Harald']:
            utils.remove_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald", node_id)

        h = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt1, "node/affiliation/owner/com.ericsson")
        h_ = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Harald")

        if h_['result'] is not None:
            # Test that the storage is local
            warn("Storage is no longer only local, it had time to start %s" % h_['result'])
        assert(set(h['result']) == set([common]))
        assert(set(p['result']) == set(lindex["Per"][1:] + [common]))
        assert(set(e['result']) == set(lindex["Per"][1:] + [common]))

        time.sleep(2)
        h = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson")

        assert(set(h['result']) == set([common]))
        assert(set(p['result']) == set(lindex["Per"][1:] + [common]))
        assert(set(e['result']) == set(lindex["Per"][1:] + [common]))

    @pytest.mark.slow
    def testGlobalIndex(self):
        time.sleep(2)
        lindex = {}
        lindex['Harald'] = [calvinuuid.uuid("NODE") for i in range(1,5)]
        lindex['Per'] = [calvinuuid.uuid("NODE") for i in range(1,5)]
        common = calvinuuid.uuid("NODE")

        for n, node_ids in lindex.items():
            for id_ in node_ids:
                #print "ADD", n, id_
                utils.add_index(self.rt1, "node/affiliation/owner/com.ericsson/" + n, id_)

        h = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson")

        assert(set(h['result']) == set(lindex["Harald"]))
        assert(set(p['result']) == set(lindex["Per"]))
        assert(set(e['result']) == set(lindex["Per"] + lindex["Harald"]))

        for n, node_ids in lindex.items():
            utils.remove_index(self.rt1, "node/affiliation/owner/com.ericsson/" + n, node_ids[0])

        h = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson")

        assert(set(h['result']) == set(lindex["Harald"][1:]))
        assert(set(p['result']) == set(lindex["Per"][1:]))
        assert(set(e['result']) == set(lindex["Per"][1:] + lindex["Harald"][1:]))

        utils.add_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald", common)
        utils.add_index(self.rt1, "node/affiliation/owner/com.ericsson/Per", common)

        h = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson")

        assert(set(h['result']) == set(lindex["Harald"][1:] + [common]))
        assert(set(p['result']) == set(lindex["Per"][1:] + [common]))
        assert(set(e['result']) == set(lindex["Per"][1:] + lindex["Harald"][1:] + [common]))

        for node_id in lindex['Harald']:
            utils.remove_index(self.rt1, "node/affiliation/owner/com.ericsson/Harald", node_id)

        h = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Harald")
        p = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson/Per")
        e = utils.get_index(self.rt2, "node/affiliation/owner/com.ericsson")

        assert(set(h['result']) == set([common]))
        assert(set(p['result']) == set(lindex["Per"][1:] + [common]))
        assert(set(e['result']) == set(lindex["Per"][1:] + [common]))


class CalvinNodeTestBase(unittest.TestCase):

    def setUp(self):
        self.rt1 = dispatch_node("calvinip://localhost:5000", "http://localhost:5003",
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})

        self.rt2 = dispatch_node("calvinip://localhost:5001", "http://localhost:5004",
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})
        self.rt3 = dispatch_node("calvinip://localhost:5002", "http://localhost:5005",
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner2'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode3'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 2}}})

    def tearDown(self):
        utils.quit(self.rt1)
        utils.quit(self.rt2)
        utils.quit(self.rt3)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        time.sleep(0.2)


@pytest.mark.slow
class TestNodeIndex(CalvinNodeTestBase):
    @pytest.mark.slow
    def testNodeIndexThree(self):
        time.sleep(4)

        print self.rt1.id, self.rt2.id, self.rt3.id

        owner1 = utils.get_index(self.rt1, format_index_string({'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'}}))
        assert(set(owner1['result']) == set([self.rt1.id, self.rt2.id]))

        owner2 = utils.get_index(self.rt1, format_index_string({'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner2'}}))
        assert(set(owner2['result']) == set([self.rt3.id]))

        owners = utils.get_index(self.rt1, format_index_string({'owner':{'organization': 'org.testexample'}}))
        assert(set(owners['result']) == set([self.rt1.id, self.rt2.id, self.rt3.id]))

        names = utils.get_index(self.rt1, format_index_string({'node_name':{}}))
        assert(set(names['result']) == set([self.rt1.id, self.rt2.id, self.rt3.id]))

        addr2 = utils.get_index(self.rt1, format_index_string({'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 2}}))
        assert(set(addr2['result']) == set([self.rt3.id]))

@pytest.mark.slow
class CalvinNodeTestIndexAll(unittest.TestCase):

    def setUp(self):
        self.hosts = []
        self.rt = []

    def tearDown(self):
        for r in self.rt:
            utils.quit(r)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        time.sleep(0.2)

    @pytest.mark.slow
    def testNodeIndexMany(self):
        """ Since storage is eventually consistent, and we don't really know when,
            this test is quite loose on its asserts but shows some warnings when
            inconsistent. It is also extremly slow.
        """
        self.hosts = [("calvinip://127.0.0.1:%d" % d, "http://localhost:%d" % (d+1), "owner%d" % ((d-5000)/2)) for d in range(5000, 5041, 2)]
        self.rt = [dispatch_node(h[0], h[1], attributes={'indexed_public': {'owner':{'personOrGroup': h[2]}}}) for h in self.hosts]
        time.sleep(3)
        owner = []
        for i in range(len(self.hosts)):
            res = utils.get_index(self.rt[0], format_index_string({'owner':{'personOrGroup': self.hosts[i][2]}}))
            owner.append(res)
            assert(set(res['result']) == set([self.rt[i].id]))

        owners = utils.get_index(self.rt[0], format_index_string({'owner':{}}))
        assert(set(owners['result']) <= set([r.id for r in self.rt]))
        if set(owners['result']) == set([r.id for r in self.rt]):
            warn("Not all nodes manage to reach the index")
        rt = self.rt[:]
        ids = [r.id for r in rt]
        hosts = self.hosts[:]
        utils.quit(self.rt[10])
        del self.rt[10]
        del self.hosts[10]
        owners = utils.get_index(self.rt[0], format_index_string({'owner':{}}))
        assert(set(owners['result']) <= set(ids))
        if ids[10] in set(owners['result']):
            warn("The removed node is still in the all owners set")

        removed_owner = utils.get_index(self.rt[0], format_index_string({'owner':{'personOrGroup': hosts[10][2]}}))
        assert(not removed_owner['result'] or set(removed_owner['result']) == set([ids[10]]))
        if removed_owner['result']:
            warn("The removed node is still in its own index")

        # Destroy a bunch of the nodes
        for _ in range(7):
            utils.quit(self.rt[10])
            del self.rt[10]
            del self.hosts[10]

        time.sleep(2)
        owners = utils.get_index(self.rt[0], format_index_string({'owner':{}}))
        assert(set(owners['result']) <= set(ids))
        l = len(set(owners['result']))
        if l > (len(ids)-8):
            warn("Did have %d nodes left even after removal of 8 from %d" % (l, len(ids)))