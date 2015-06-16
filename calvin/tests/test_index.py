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
            warn("Storage is no longer only local, it had time to start")
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


