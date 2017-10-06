# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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
import sys
import os
import random
import time
import json
import uuid
import Queue
import multiprocessing
import traceback
from functools import partial
import unittest

from mock import Mock
from twisted.internet import reactor, defer

from calvin.utilities import calvinuuid
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
from calvin.utilities.calvin_callback import CalvinCB, CalvinCBClass
from calvin.runtime.south.plugins.async import threads, async
from calvin.runtime.north import storage, calvin_proto
from calvin.requests import calvinresponse
from calvin.tests.helpers_twisted import create_callback, wait_for
import calvin.tests

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

storage_types = ["notstarted", "dht", "proxy", "sql"]
#storage_types = ["dht"]

class FakeTunnel(calvin_proto.CalvinTunnel):
    def send(self, payload):
        #print "### SEND", payload
        # Directly call peers receive method
        self._peers_fake_tunnel.recv_handler(payload)

class DummyNetwork(Mock):
    def __init__(self, node, *args, **kwargs):
        self.__dict__["node"] = node
        return super(Mock, self).__init__(*args, **kwargs)

    def join(self, uris, callback, *args, **kwargs):
        #print "### JOIN", uris, callback, args, kwargs
        masterid = self.node.master_node.id  # We always join the master in this test
        async.DelayedCall(0, callback, 200, None, masterid)

class DummyProto(Mock):
    def __init__(self, node, *args, **kwargs):
        self.__dict__["node"] = node
        return super(Mock, self).__init__(*args, **kwargs)

    def tunnel_new(self, to_rt_uuid, tunnel_type, policy):
        #print "### TUNNEL_NEW", to_rt_uuid, tunnel_type, policy
        # Pick the available fake tunnel
        return self.node.tunnels[self.node.id][to_rt_uuid]

# So it skips if we dont have twisted plugin
def _dummy_inline(*args):
    pass

if not hasattr(pytest, 'inlineCallbacks'):
    pytest.inlineCallbacks = _dummy_inline

@pytest.fixture(autouse=True, scope="module")
def setup(request):
    # Create 3 test nodes per storage type
    print "###SETUP"
    tunnels = {}
    nodes = {}
    for ti in range(len(storage_types)):
        nodes[storage_types[ti]] = [calvin.tests.TestNode(["calvinip://127.0.0.1:50{}{}".format(ti, i)]) for i in range(3)]

    def prep_node(stype, n):
        n.storage = storage.Storage(n)
        if stype == "proxy":
            try:
                n.network = DummyNetwork(n)
                n.proto = DummyProto(n)
            except:
                traceback.print_exc()
        if stype != "notstarted" :
            cb, d = create_callback(timeout=10)
            n.storage.start(cb=cb)
            return d

    all_started = []
    for ti in range(len(storage_types)):
        stype = storage_types[ti]
        if stype == "dht":
            try:
                _conf.set('global', 'storage_type', 'dht')
                all_started.extend(map(partial(prep_node, stype), nodes[stype]))
            except:
                traceback.print_exc()
        elif stype == "notstarted":
            _conf.set('global', 'storage_type', 'dht')
            map(partial(prep_node, stype), nodes[stype])
        elif stype == "sql":
            _conf.set('global', 'storage_type', 'sql')
            _conf.set('global', 'storage_sql', {})  # Use the default, i.e. local passwd-less root mysql DB
            all_started.extend(map(partial(prep_node, stype), nodes[stype]))
        elif stype == "proxy":
            # Setting up proxy storage for testing is a bit complicated
            # We short circuit so that fake tunnels' send directly calls peer's receive-method
            # The master (0) is setup as local and the others (1,2) as proxy
            # Give the master node ref to the proxies (to be used in fake network, proto & tunnel)
            nodes["proxy"][1].master_node = nodes["proxy"][0]
            nodes["proxy"][2].master_node = nodes["proxy"][0]
            # Create fake tunnels
            for n2 in nodes["proxy"]:
                tt = {}
                for n1 in nodes["proxy"]:
                     if n1 != n2:
                         tt[n1.id] = FakeTunnel(
                                        DummyNetwork(n1),
                                        tt,
                                        n1.id,
                                        'storage',
                                        None,
                                        rt_id=n2.id,
                                        id=calvinuuid.uuid("TUNNEL")) 
                tunnels[n2.id] = tt
                n2.tunnels = tunnels
            # Give a tunnel its peers tunnel
            for n2 in nodes["proxy"]:
                for n1 in nodes["proxy"]:
                     if n1 != n2:
                         tunnels[n2.id][n1.id]._peers_fake_tunnel = tunnels[n1.id][n2.id]
            # Start master
            _conf.set('global', 'storage_type', 'local')
            prep_node(stype, nodes[stype][0])
            # Inform master it has 2 proxy storage clients
            [nodes[stype][0].storage.tunnel_request_handles(t) for t in tunnels[nodes[stype][0].id].values()]
            # Start proxies
            _conf.set('global', 'storage_type', 'proxy')
            _conf.set('global', 'storage_proxy', nodes[stype][0].uris[0])
            all_started.extend(map(partial(prep_node, stype), nodes[stype][1:]))
            # Inform proxy that it is connected, first wait until up_handler set
            count = 0
            while (tunnels[nodes[stype][1].id][nodes[stype][0].id].up_handler is None or
                   tunnels[nodes[stype][2].id][nodes[stype][0].id].up_handler is None) and count < 100:
                   pytest.blockon(threads.defer_to_thread(time.sleep, 0.1))
                   count += 1
            tunnels[nodes[stype][1].id][nodes[stype][0].id].up_handler()
            tunnels[nodes[stype][2].id][nodes[stype][0].id].up_handler()
    dl = defer.DeferredList(all_started)
    print time.time()
    try:
        pytest.blockon(dl)
    except:
        print "### Some storage plugins might have failed to start! ###"
        traceback.print_exc()
    print time.time()
    return {"nodes": nodes}

@pytest.mark.essential
@pytest.mark.skipif(pytest.inlineCallbacks == _dummy_inline,
                    reason="No inline twisted plugin enabled, please use --twisted to py.test")
class TestAllStorage(object):
    """ Test that all storage plugin types functionality is identical and correct.
    """
    @pytest.inlineCallbacks
    def teardown(self):
        yield threads.defer_to_thread(time.sleep, .001)

    def _test_done(self):
        return self.done

    def cb(self, key, value):
        self.get_ans = value
        self.done = True

    def cb2(self, value):
        self.get_ans = value
        self.done = True

    def verify_started(self):
        """ Test that all the plugins that should have started have done so. """
        for stype in storage_types:
            if stype == "notstarted":
                # Not started storage is never started
                continue
            for y in range(3):
                if stype == "proxy" and y == 0:
                    # The first node in proxy is the local master which is never started
                    continue
                assert self.nodes[stype][y].storage.started

    @pytest.inlineCallbacks
    def test_set_get(self, setup):
        """ Test that set returns OK and get returns value set """
        self.nodes = setup.get("nodes")
        self.verify_started()
        for stype in storage_types:
            for i in ["aa", "bb", "", None, True, False, 0, 1, 2, [0, 1], {"xx": 10}]:
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.set("test-", key + str(y), i, CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "set response", self.get_ans, stype, key, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.nodes[stype][x].storage.get("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        assert self.get_ans == i

    @pytest.inlineCallbacks
    def test_set_delete_get(self, setup):
        """ Test that set returns OK, delete return OK and get returns 404 response """
        self.nodes = setup.get("nodes")
        self.verify_started()
        for stype in storage_types:
            for i in ["aa", "bb", "cc", "", None, True, False, 0, 1, 2, [0, 1], {"xx": 10}]:
                for y in range(3):
                    key = "t2" + str(i)
                    if i != "cc":
                        # "cc" is missing without being set and deleted
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.set("test-", key + str(y), i, CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "set response", self.get_ans, stype, i, y
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.delete("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "delete response", self.get_ans, stype, i, y
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.nodes[stype][x].storage.get("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get response", self.get_ans, stype, i, x
                        # Verify the response is 404
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.NOT_FOUND

    @pytest.inlineCallbacks
    def test_append_getconcat(self, setup):
        """ Test that single value append returns OK and get_concat returns appended value in list """
        self.nodes = setup.get("nodes")
        self.verify_started()
        for stype in storage_types:
            for i in ["aa", "bb", "", True, False, 0, 1, 2]:  # values must be hashable (i.e. not list or dict)
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test-", key + str(y), [i], CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "append response", self.get_ans, stype, key, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.nodes[stype][x].storage.get_concat("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_concat response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        assert self.get_ans == [i]

    @pytest.inlineCallbacks
    def test_append_multi_getconcat(self, setup):
        """ Test that appending multiple values returns OK and get_concat returns the unique values (set) in a list """
        self.nodes = setup.get("nodes")
        self.verify_started()
        for stype in storage_types:
            for i in [("aa", "aa"), ("bb", 2, "ff"), (True, ""), (False, True)]:  # values must be hashable (i.e. not list or dict)
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test-", key + str(y), i, CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "append response", self.get_ans, stype, key, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][x].storage.get_concat("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_concat response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        assert set(self.get_ans) == set(i)

    @pytest.inlineCallbacks
    def test_append_multi_remove_getconcat(self, setup):
        """ Test that appending multiple values returns OK, remove a value returns OK
             and get_concat returns the unique values (set) in a list """
        self.nodes = setup.get("nodes")
        self.verify_started()
        for stype in storage_types:
            for i in [("aa", "aa"), ("bb", 2, "ff"), (0, 1, 2, 3)]:  # values must be hashable (i.e. not list or dict)
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test-", key + str(y), i, CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "append response", self.get_ans, stype, key, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.remove("test-", key + str(y), i[1:], CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "append response", self.get_ans, stype, key, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][x].storage.get_concat("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_concat response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        answer = set(i) - set(i[1:])
                        assert set(self.get_ans) == answer

    @pytest.inlineCallbacks
    def test_append_delete_get_concat(self, setup):
        """ Test that append returns OK, delete return OK and get returns empty set """
        self.nodes = setup.get("nodes")
        self.verify_started()
        for stype in storage_types:
            for i in ["aa", None, True, False, 0, 1, 2]:
                for y in range(3):
                    key = "t3" + str(i)
                    if i != "cc":
                        # "cc" is missing without being set and deleted
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.append("test-", key + str(y), [i], CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "append response", self.get_ans, stype, i, y
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.delete("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "delete response", self.get_ans, stype, i, y
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.nodes[stype][x].storage.get_concat("test-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_concat response", self.get_ans, stype, i, x
                        # Verify the response is empty list (no difference between emptied or deleted)
                        assert self.get_ans == []

