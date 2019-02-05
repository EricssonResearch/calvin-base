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
import os
import copy
import time
import shutil
import traceback
from functools import partial

from mock import Mock
from twisted.internet import reactor, defer

from calvin.utilities import calvinuuid
from calvin.utilities import calvinlogger
import calvin.utilities.calvinconfig
from calvin.utilities.utils import get_home
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.south.async import threads, async
from calvin.runtime.north import storage, calvin_proto
from calvin.requests import calvinresponse
from calvin.tests.helpers_twisted import create_callback, wait_for
import calvin.tests
from calvin.tests import helpers
from calvin.utilities import attribute_resolver

#FIXME Can't get cert chain to work for securedht (maybe because secure conf is read also after started)
import calvin.utilities.certificate
def chain_dummy(*args, **kwargs):
    pass
calvin.utilities.certificate.verify_certificate_chain = chain_dummy

_log = calvinlogger.get_logger(__name__)
_conf = calvin.utilities.calvinconfig.get()

storage_types = ["notstarted", "dht", "securedht", "proxy"]
# Removing the SQL-tests temporarily
# storage_types = ["notstarted", "dht", "securedht", "proxy", "sql"]

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

@pytest.fixture(autouse=True, scope="class")
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
            cb, d = create_callback(timeout=10, test_part=stype + " start")
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
        elif stype == "securedht":
            try:
                homefolder = get_home()
                credentials_testdir = os.path.join(homefolder, ".calvin","test_all_storage_dir")
                runtimesdir = os.path.join(credentials_testdir,"runtimes")
                security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
                domain_name="test_security_domain"
                code_signer_name="test_signer"
                orig_identity_provider_path = os.path.join(security_testdir,"identity_provider")
                identity_provider_path = os.path.join(credentials_testdir, "identity_provider")
                policy_storage_path = os.path.join(security_testdir, "policies")
                try:
                    shutil.rmtree(credentials_testdir)
                except Exception as err:
                    print "Failed to remove old tesdir, err={}".format(err)
                    pass
                try:
                    shutil.copytree(orig_identity_provider_path, identity_provider_path)
                except Exception as err:
                    _log.error("Failed to copy the identity provider files, err={}".format(err))
                    raise
                runtimes = helpers.create_CA_and_generate_runtime_certs(domain_name, credentials_testdir, 3)

                for r, n in zip(runtimes, nodes[stype]):
                    n.attributes = attribute_resolver.AttributeResolver(r['attributes'])
                    n.enrollment_password = r['enrollment_password']
                    n.id = r['id']
                    n.runtime_credentials = r['credentials']
                    n.node_name = r['node_name']

                #print "###RUNTIMES", runtimes

                _conf.add_section("security")
                _conf.set('security', 'security_dir', credentials_testdir)
                _conf.set('global','storage_type','securedht')
                all_started.extend(map(partial(prep_node, stype), nodes[stype]))
                _conf.remove_section("security")
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
    def teardown():
        print "#####TEARDOWN"
        all_stopped = []
        for ntypes in nodes.values():
            for n in ntypes:
                cb, d = create_callback(timeout=10)
                n.storage.stop(cb=cb)
                all_stopped.append(d)
        dl = defer.DeferredList(all_stopped)
        try:
            pytest.blockon(dl)
        except:
            print "### Some storage plugins might have failed to stopp ###"
            traceback.print_exc()
    request.addfinalizer(teardown)
    return {"nodes": nodes}

@pytest.mark.essential
@pytest.mark.skipif(pytest.inlineCallbacks.__name__ == "_dummy_inline",
                    reason="No inline twisted plugin enabled, please use --twisted to py.test")
class TestAllStorage(object):
    """ Test that all storage plugin types functionality is identical and correct.
    """
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
        working = []
        for stype in storage_types:
            if stype == "notstarted":
                # Not started storage is never started
                working.append(stype)
                continue
            for y in range(3):
                if stype == "proxy" and y == 0:
                    # The first node in proxy is the local master which is never started
                    continue
                if not self.nodes[stype][y].storage.started:
                    break
                if y == 2:
                    # All started for stype plugin
                    working.append(stype)
        return working

    @pytest.inlineCallbacks
    def test_set_get(self, setup):
        """ Test that set returns OK and get returns value set """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for i in ["aa", "bb", "", None, True, False, 0, 1, 2, [0, 1], {"xx": 10}]:
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.set("test1-", key + str(y), i, CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "set response", self.get_ans, stype, key, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][x].storage.get("test1-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        assert self.get_ans == i

    @pytest.inlineCallbacks
    def test_set_delete_get(self, setup):
        """ Test that set returns OK, delete return OK and get returns 404 response """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for i in ["aa", "bb", "cc", "", None, True, False, 0, 1, 2, [0, 1], {"xx": 10}]:
                for y in range(3):
                    key = "t2" + str(i)
                    if i != "cc":
                        # "cc" is missing without being set and deleted
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.set("test2-", key + str(y), i, CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "set response", self.get_ans, stype, i, y
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.delete("test2-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "delete response", self.get_ans, stype, i, y
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][x].storage.get("test2-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get response", self.get_ans, stype, i, x
                        # Verify the response is 404
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.NOT_FOUND

    @pytest.inlineCallbacks
    def test_append_getconcat(self, setup):
        """ Test that single value append returns OK and get_concat returns appended value in list """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for i in ["aa", "bb", "", True, False, 0, 1, 2]:  # values must be hashable (i.e. not list or dict)
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test3-", key + str(y), [i], CalvinCB(self.cb))
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
                        self.nodes[stype][x].storage.get_concat("test3-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_concat response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        assert self.get_ans == [i]

    @pytest.inlineCallbacks
    def test_append_multi_getconcat(self, setup):
        """ Test that appending multiple values returns OK and get_concat returns the unique values (set) in a list """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for i in [("aa", "aa"), ("bb", 2, "ff"), (True, ""), (False, True)]:  # values must be hashable (i.e. not list or dict)
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test4-", key + str(y), i, CalvinCB(self.cb))
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
                        self.nodes[stype][x].storage.get_concat("test4-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_concat response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        assert set(self.get_ans) == set(i)

    @pytest.inlineCallbacks
    def test_append_multi_remove_getconcat(self, setup):
        """ Test that appending multiple values returns OK, remove a value returns OK
             and get_concat returns the unique values (set) in a list """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for i in [("aa", "aa"), ("bb", 2, "ff"), (0, 1, 2, 3)]:  # values must be hashable (i.e. not list or dict)
                key = str(i)
                for y in range(3):
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test5-", key + str(y), i, CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "append response", self.get_ans, stype, key, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.remove("test5-", key + str(y), i[1:], CalvinCB(self.cb))
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
                        self.nodes[stype][x].storage.get_concat("test5-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_concat response", self.get_ans, stype, key, x
                        # Verify we read what is written
                        answer = set(i) - set(i[1:])
                        assert set(self.get_ans) == answer

    @pytest.inlineCallbacks
    def test_append_delete_get_concat(self, setup):
        """ Test that append returns OK, delete return OK and get returns empty set """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for i in ["aa", None, True, False, 0, 1, 2]:
                for y in range(3):
                    key = "t3" + str(i)
                    if i != "cc":
                        # "cc" is missing without being set and deleted
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.append("test6-", key + str(y), [i], CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10, test_part="append"+key+str(y))
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "append response", self.get_ans, stype, i, y
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][y].storage.delete("test6-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10, test_part="delete"+key+str(y))
                        # Verify response is CalvinResponse object with OK status
                        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                        print "delete response", self.get_ans, stype, i, y
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][x].storage.get_concat("test6-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10, test_part="get_concat"+key+str(y))
                        print "get_concat response", self.get_ans, stype, i, x
                        # Verify the response is empty list (no difference between emptied or deleted)
                        assert self.get_ans == []

    @pytest.inlineCallbacks
    def test_append_delete_append_get_concat(self, setup):
        """ Test that append returns OK, delete return OK and get returns second append """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for i in ["aa"]:
                for y in range(3):
                    key = "t3" + str(i)
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test7-", key + str(y), [i], CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10, test_part="append"+key+str(y))
                    # Verify response is CalvinResponse object with OK status
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    print "append response", self.get_ans, stype, i, y
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.delete("test7-", key + str(y), CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10, test_part="delete"+key+str(y))
                    # Verify response is CalvinResponse object with OK status
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    print "delete response", self.get_ans, stype, i, y
                    self.done = False
                    self.get_ans = None
                    self.nodes[stype][y].storage.append("test7-", key + str(y), [i+"2"], CalvinCB(self.cb))
                    yield wait_for(self._test_done, timeout=10, test_part="append2"+key+str(y))
                    # Verify response is CalvinResponse object with OK status
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                    print "append2 response", self.get_ans, stype, i, y
                    for x in range(3):
                        if stype == "notstarted" and x != y:
                            # Not started storage is never connected to other nodes storage
                            continue
                        self.done = False
                        self.get_ans = None
                        self.nodes[stype][x].storage.get_concat("test7-", key + str(y), CalvinCB(self.cb))
                        yield wait_for(self._test_done, timeout=10, test_part="get_concat"+key+str(y))
                        print "get_concat response", self.get_ans, stype, i, x
                        # Verify the response is second appended value
                        assert self.get_ans == [i+"2"]

    @pytest.inlineCallbacks
    def test_add_get_index(self, setup):
        """ Test that add_index returns OK and get_index returns appended value in list for index hierarchies """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for y in range(3):
                for i in [(["aa", "bb", "", "dd"], "xx"),
                          (["aa", "bb", "", "ee"], "yy"),
                          (["aa", "bb"], "zz"),
                          (["aa", "ff", "", "dd"], "xx")]:
                    self.done = False
                    self.get_ans = None
                    index = copy.copy(i[0])
                    index[0] = "test1" + index[0] + str(y)
                    # root_prefix_level is default 2 hence 2 first are combined
                    self.nodes[stype][y].storage.add_index(index, [i[1]], cb=CalvinCB(self.cb2))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "add response", self.get_ans, stype, index, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                for x in range(3):
                    if stype == "notstarted" and x != y:
                        # Not started storage is never connected to other nodes storage
                        continue
                    for i in [(["aa"], []),
                              (["gg"], []),
                              (["aa", "bb"], ["xx", "yy", "zz"]),
                              (["aa", "bb", ""], ["xx", "yy"]),
                              (["aa", "ff"], ["xx"]),
                              (["aa", "bb", "", "dd"], ["xx"]),
                              (["aa", "bb", "", "ee"], ["yy"]),
                              (["aa", "ff", "", "dd"], ["xx"])]:
                        self.done = False
                        self.get_ans = None
                        index = copy.copy(i[0])
                        index[0] = "test1" + index[0] + str(y)
                        self.nodes[stype][x].storage.get_index(index, cb=CalvinCB(self.cb2))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_index response", self.get_ans, stype, index, x
                        # Verify we read what is written if too short prefix or not existing we should get [].
                        assert set(self.get_ans) == set(i[1])

    @pytest.inlineCallbacks
    def test_add_remove_get_index(self, setup):
        """ Test that add_index returns OK, remove_index returns OK and get_index returns appended value in list for index hierarchies """
        self.nodes = setup.get("nodes")
        storage_types = self.verify_started()
        for stype in storage_types:
            for y in range(3):
                for i in [(["aa", "bb", "", "dd"], ["xx", "kk", "ll"], "+"),
                          (["aa", "bb", "", "ee"], ["yy", "kk", "ll"], "+"),
                          (["aa", "bb"], ["zz", "mm", "oo"], "+"),
                          (["aa", "ff", "", "dd"], ["xx"], "+"),
                          (["aa", "bb", "", "dd"], ["kk", "ll"], "-"),
                          (["aa", "bb", "", "ee"], ["yy", "kk", "ll"], "-"),
                          (["aa", "bb"], ["oo"], "-"),
                          (["aa", "gg", "", "dd"], ["xx"], "-")
                          ]:
                    self.done = False
                    self.get_ans = None
                    index = copy.copy(i[0])
                    index[0] = "test2" + index[0] + str(y)
                    # root_prefix_level is default 2 hence 2 first are combined
                    if i[2] == "+":
                        self.nodes[stype][y].storage.add_index(index, i[1], cb=CalvinCB(self.cb2))
                    else:
                        self.nodes[stype][y].storage.remove_index(index, i[1], cb=CalvinCB(self.cb2))
                    yield wait_for(self._test_done, timeout=10)
                    # Verify response is CalvinResponse object with OK status
                    print "add" if i[2] == "+" else "remove", " response", self.get_ans, stype, index, y
                    assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK
                for x in range(3):
                    if stype == "notstarted" and x != y:
                        # Not started storage is never connected to other nodes storage
                        continue
                    for i in [(["aa"], []),
                              (["gg"], []),
                              (["aa", "gg"], []),
                              (["aa", "bb"], ["xx", "zz", "mm"]),
                              (["aa", "bb", ""], ["xx"]),
                              (["aa", "ff"], ["xx"]),
                              (["aa", "bb", "", "dd"], ["xx"]),
                              (["aa", "bb", "", "ee"], []),
                              (["aa", "ff", "", "dd"], ["xx"])]:
                        self.done = False
                        self.get_ans = None
                        index = copy.copy(i[0])
                        index[0] = "test2" + index[0] + str(y)
                        self.nodes[stype][x].storage.get_index(index, cb=CalvinCB(self.cb2))
                        yield wait_for(self._test_done, timeout=10)
                        print "get_index response", self.get_ans, stype, index, x
                        # Verify we read what is written if too short prefix or not existing we should get [].
                        assert set(self.get_ans) == set(i[1])

    def test_all_started(self, setup):
        self.nodes = setup.get("nodes")
        assert storage_types == self.verify_started()

