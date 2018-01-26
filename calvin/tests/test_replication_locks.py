# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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
import unittest
import time
from calvin.tests import DummyNode

from calvin.runtime.north.replicationmanager import ReplicationData, ReplicationManager

pytestmark = pytest.mark.unittest

class TestLocalEndpoint(unittest.TestCase):

    def setUp(self):
        self.rm = ReplicationManager(DummyNode())
        self.rm.managed_replications = {"RM1": ReplicationData(), "RM2":ReplicationData()}
        for rid, r in self.rm.managed_replications.items():
            r.id = rid
            r.peer_replication_ids = self.rm.managed_replications.keys()
            r.peer_replication_ids.remove(rid)
        # Make both rm ids local
        self.rm.leaders_cache = {"RM1": self.rm.node.id, "RM2": self.rm.node.id}

    def test_lock1(self):
        print "Test: local"
        self.rm.lock_peer_replication("RM1", self._response1)
        print "lock"
        self._print_lock_lists()
        self.rm.release_peer_replication("RM1")
        print "released 1"
        self._print_lock_lists()
        assert "RM1" not in self.rm.managed_replications["RM2"].given_lock_replication_ids
        assert "RM2" not in self.rm.managed_replications["RM1"].aquired_lock_replication_ids
        self.rm.lock_peer_replication("RM1", self._response2)
        self.rm.lock_peer_replication("RM2", self._response3)
        print "queued"
        self._print_lock_lists()
        assert "RM1" in self.rm.managed_replications["RM2"].queued_lock_replication_ids
        self.rm.release_peer_replication("RM1")
        print "release 1 -> lock"
        self._print_lock_lists()
        assert "RM2" in self.rm.managed_replications["RM1"].given_lock_replication_ids
        assert "RM1" in self.rm.managed_replications["RM2"].aquired_lock_replication_ids
        self.rm.release_peer_replication("RM2")
        print "released 2"
        self._print_lock_lists()
        assert "RM2" not in self.rm.managed_replications["RM1"].given_lock_replication_ids
        assert "RM1" not in self.rm.managed_replications["RM2"].aquired_lock_replication_ids

    def _print_lock_lists(self):
        print "RM1 given  ", self.rm.managed_replications["RM1"].given_lock_replication_ids
        print "RM1 aquired", self.rm.managed_replications["RM1"].aquired_lock_replication_ids
        print "RM1 queued ", self.rm.managed_replications["RM1"].queued_lock_replication_ids
        print "RM2 given  ", self.rm.managed_replications["RM2"].given_lock_replication_ids
        print "RM2 aquired", self.rm.managed_replications["RM2"].aquired_lock_replication_ids
        print "RM2 queued ", self.rm.managed_replications["RM2"].queued_lock_replication_ids

    def _response1(self, status):
        print "response1", status
        self._print_lock_lists()
        assert "RM1" in self.rm.managed_replications["RM2"].given_lock_replication_ids
        assert "RM2" in self.rm.managed_replications["RM1"].aquired_lock_replication_ids

    def _response2(self, status):
        print "response2", status
        self._print_lock_lists()
        assert "RM1" in self.rm.managed_replications["RM2"].given_lock_replication_ids
        assert "RM2" in self.rm.managed_replications["RM1"].aquired_lock_replication_ids

    def _response3(self, status):
        print "response3", status
        self._print_lock_lists()
        assert "RM2" in self.rm.managed_replications["RM1"].given_lock_replication_ids
        assert "RM1" in self.rm.managed_replications["RM2"].aquired_lock_replication_ids

