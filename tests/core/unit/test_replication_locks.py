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

from calvin.runtime.north.replicationmanager import ReplicationData, ReplicationManager


@pytest.fixture()
def _replication_manager(dummy_node):
    """Return ReplicationManager instance"""
    rm = ReplicationManager(dummy_node)
    rm.managed_replications = {"RM1": ReplicationData(), "RM2":ReplicationData()}
    for rid, r in list(rm.managed_replications.items()):
        r.id = rid
        r.peer_replication_ids = list(rm.managed_replications.keys())
        r.peer_replication_ids.remove(rid)
    # Make both rm ids local
    rm.leaders_cache = {"RM1": rm.node.id, "RM2": rm.node.id}
    return rm

def test_lock1(_replication_manager):
    
    def _print_lock_lists():
        print("RM1 given  ", _replication_manager.managed_replications["RM1"].given_lock_replication_ids)
        print("RM1 aquired", _replication_manager.managed_replications["RM1"].aquired_lock_replication_ids)
        print("RM1 queued ", _replication_manager.managed_replications["RM1"].queued_lock_replication_ids)
        print("RM2 given  ", _replication_manager.managed_replications["RM2"].given_lock_replication_ids)
        print("RM2 aquired", _replication_manager.managed_replications["RM2"].aquired_lock_replication_ids)
        print("RM2 queued ", _replication_manager.managed_replications["RM2"].queued_lock_replication_ids)
    
    def _response1(status):
        print("response1", status)
        _print_lock_lists()
        assert "RM1" in _replication_manager.managed_replications["RM2"].given_lock_replication_ids
        assert "RM2" in _replication_manager.managed_replications["RM1"].aquired_lock_replication_ids

    def _response2(status):
        print("response2", status)
        _print_lock_lists()
        assert "RM1" in _replication_manager.managed_replications["RM2"].given_lock_replication_ids
        assert "RM2" in _replication_manager.managed_replications["RM1"].aquired_lock_replication_ids

    def _response3(status):
        print("response3", status)
        _print_lock_lists()
        assert "RM2" in _replication_manager.managed_replications["RM1"].given_lock_replication_ids
        assert "RM1" in _replication_manager.managed_replications["RM2"].aquired_lock_replication_ids
    
    print("Test: local")
    _replication_manager.lock_peer_replication("RM1", _response1)
    print("lock")
    _print_lock_lists()
    _replication_manager.release_peer_replication("RM1")
    print("released 1")
    _print_lock_lists()
    assert "RM1" not in _replication_manager.managed_replications["RM2"].given_lock_replication_ids
    assert "RM2" not in _replication_manager.managed_replications["RM1"].aquired_lock_replication_ids
    _replication_manager.lock_peer_replication("RM1", _response2)
    _replication_manager.lock_peer_replication("RM2", _response3)
    print("queued")
    _print_lock_lists()
    assert "RM1" in _replication_manager.managed_replications["RM2"].queued_lock_replication_ids
    _replication_manager.release_peer_replication("RM1")
    print("release 1 -> lock")
    _print_lock_lists()
    assert "RM2" in _replication_manager.managed_replications["RM1"].given_lock_replication_ids
    assert "RM1" in _replication_manager.managed_replications["RM2"].aquired_lock_replication_ids
    _replication_manager.release_peer_replication("RM2")
    print("released 2")
    _print_lock_lists()
    assert "RM2" not in _replication_manager.managed_replications["RM1"].given_lock_replication_ids
    assert "RM1" not in _replication_manager.managed_replications["RM2"].aquired_lock_replication_ids



