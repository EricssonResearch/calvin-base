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

import os
import unittest
import time
import pytest
import multiprocessing

from calvin.csparser import cscompile as compiler
from calvin.Tools import deployer
from calvin.utilities import calvinconfig
from calvin.utilities import calvinlogger
from calvin.utilities.nodecontrol import dispatch_node
from calvin.utilities.attribute_resolver import format_index_string
from calvin.requests.request_handler import RequestHandler, RT


_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

def actual_tokens(rt, actor_id):
    return request_handler.report(rt, actor_id)

def expected_counter(n):
    return [i for i in range(1, n + 1)]

def cumsum(l):
    s = 0
    for n in l:
        s = s + n
        yield s

def expected_sum(n):
    return list(cumsum(range(1, n + 1)))

def expected_tokens(rt, actor_id, src_actor_type):
    tokens = request_handler.report(rt, actor_id)

    if src_actor_type == 'std.CountTimer':
        return expected_counter(tokens)

    if src_actor_type == 'std.Sum':
        return expected_sum(tokens)

    return None

runtime = None
runtimes = []
peerlist = []
kill_peers = True
request_handler = None

def setup_module(module):
    global runtime
    global runtimes
    global peerlist
    global kill_peers
    global request_handler
    ip_addr = None
    bt_master_controluri = None

    request_handler = RequestHandler()
    try:
        ip_addr = os.environ["CALVIN_TEST_IP"]
        purpose = os.environ["CALVIN_TEST_UUID"]
    except KeyError:
        pass

    if ip_addr is None:
        # Bluetooth tests assumes one master runtime with two connected peers
        # CALVIN_TEST_BT_MASTERCONTROLURI is the control uri of the master runtime
        try:
            bt_master_controluri = os.environ["CALVIN_TEST_BT_MASTERCONTROLURI"]
            _log.debug("Running Bluetooth tests")
        except KeyError:
            pass

    if ip_addr:
        remote_node_count = 2
        kill_peers = False
        test_peers = None


        import socket
        ports=[]
        for a in range(2):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('', 0))
            addr = s.getsockname()
            ports.append(addr[1])
            s.close()

        runtime,_ = dispatch_node(["calvinip://%s:%s" % (ip_addr, ports[0])], "http://%s:%s" % (ip_addr, ports[1]))

        _log.debug("First runtime started, control http://%s:%s, calvinip://%s:%s" % (ip_addr, ports[1], ip_addr, ports[0]))

        interval = 0.5
        for retries in range(1,20):
            time.sleep(interval)
            _log.debug("Trying to get test nodes for 'purpose' %s" % purpose)
            test_peers = request_handler.get_index(runtime, format_index_string({'node_name':
                                                                         {'organization': 'com.ericsson',
                                                                          'purpose': purpose}
                                                                      }))
            if not test_peers is None and not test_peers["result"] is None and \
                    len(test_peers["result"]) == remote_node_count:
                test_peers = test_peers["result"]
                break

        if test_peers is None or len(test_peers) != remote_node_count:
            _log.debug("Failed to find all remote nodes within time, peers = %s" % test_peers)
            raise Exception("Not all nodes found dont run tests, peers = %s" % test_peers)

        test_peer2_id = test_peers[0]
        test_peer2 = request_handler.get_node(runtime, test_peer2_id)
        if test_peer2:
            runtime2 = RT(test_peer2["control_uri"])
            runtime2.id = test_peer2_id
            runtime2.uri = test_peer2["uri"]
            runtimes.append(runtime2)
        test_peer3_id = test_peers[1]
        if test_peer3_id:
            test_peer3 = request_handler.get_node(runtime, test_peer3_id)
            if test_peer3:
                runtime3 = RT(test_peer3["control_uri"])
                runtime3.id = test_peer3_id
                runtime3.uri = test_peer3["uri"]
                runtimes.append(runtime3)
    elif bt_master_controluri:
        runtime = RT(bt_master_controluri)
        bt_master_id = request_handler.get_node_id(bt_master_controluri)
        data = request_handler.get_node(runtime, bt_master_id)
        if data:
            runtime.id = bt_master_id
            runtime.uri = data["uri"]
            test_peers = request_handler.get_nodes(runtime)
            test_peer2_id = test_peers[0]
            test_peer2 = request_handler.get_node(runtime, test_peer2_id)
            if test_peer2:
                rt2 = RT(test_peer2["control_uri"])
                rt2.id = test_peer2_id
                rt2.uri = test_peer2["uri"]
                runtimes.append(rt2)
            test_peer3_id = test_peers[1]
            if test_peer3_id:
                test_peer3 = request_handler.get_node(runtime, test_peer3_id)
                if test_peer3:
                    rt3 = request_handler.RT(test_peer3["control_uri"])
                    rt3.id = test_peer3_id
                    rt3.uri = test_peer3["uri"]
                    runtimes.append(rt3)
    else:
        try:
            ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
        except:
            import socket
            ip_addr = socket.gethostbyname(socket.gethostname())
        localhost = "calvinip://%s:5000" % (ip_addr,), "http://localhost:5001"
        remotehosts = [("calvinip://%s:%d" % (ip_addr, d), "http://localhost:%d" % (d+1)) for d in range(5002, 5005, 2)]
        # remotehosts = [("calvinip://127.0.0.1:5002", "http://localhost:5003")]

        for host in remotehosts:
            runtimes += [dispatch_node([host[0]], host[1])[0]]

        runtime, _ = dispatch_node([localhost[0]], localhost[1])

        time.sleep(1)

        # FIXME When storage up and running peersetup not needed, but still useful during testing
        request_handler.peer_setup(runtime, [i[0] for i in remotehosts])

        time.sleep(0.5)
        """

        # FIXME Does not yet support peerlist
        try:
            self.peerlist = peerlist(
                self.runtime, self.runtime.id, len(remotehosts))

            # Make sure all peers agree on network
            [peerlist(self.runtime, p, len(self.runtimes)) for p in self.peerlist]
        except:
            self.peerlist = []
        """

    peerlist = [rt.control_uri for rt in runtimes]
    print "SETUP DONE ***", peerlist


def teardown_module(module):
    global runtime
    global runtimes
    global kill_peers

    if kill_peers:
        for peer in runtimes:
            request_handler.quit(peer)
            time.sleep(0.2)
    request_handler.quit(runtime)
    time.sleep(0.2)
    for p in multiprocessing.active_children():
        p.terminate()
        time.sleep(0.2)

class CalvinTestBase(unittest.TestCase):

    def assertListPrefix(self, expected, actual, allow_empty=False):
        assert actual
        if len(expected) > len(actual):
            self.assertListEqual(expected[:len(actual)], actual)
        elif len(expected) < len(actual):
            self.assertListEqual(expected, actual[:len(expected)])
        else :
            self.assertListEqual(expected, actual)

    def setUp(self):
        self.runtime = runtime
        self.runtimes = runtimes
        self.peerlist = peerlist

    def compile_script(self, script, name):
        # Instead of rewriting tests after compiler.compile_script changed
        # from returning app_info, errors, warnings to app_info, issuetracker
        # use this stub in tests to keep old behaviour
        app_info, issuetracker = compiler.compile_script(script, name)
        return app_info, issuetracker.errors(), issuetracker.warnings()

@pytest.mark.slow
@pytest.mark.essential
class TestNodeSetup(CalvinTestBase):

    """Testing starting a node"""

    def testStartNode(self):
        """Testing starting node"""

        print "### testStartNode ###", self.runtime
        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist
        print "GOT RT"
        assert request_handler.get_node(rt, id_)['uri'] == rt.uri
        print "GOT URI", rt.uri


@pytest.mark.essential
@pytest.mark.slow
class TestLocalConnectDisconnect(CalvinTestBase):

    """Testing local connect/disconnect/re-connect"""

    def testLocalSourceSink(self):
        """Testing local source and sink"""

        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist

        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        request_handler.connect(rt, snk, 'token', id_, src, 'integer')

        time.sleep(0.4)

        # disable(rt, id_, src)
        request_handler.disconnect(rt, src)

        expected = expected_tokens(rt, src, 'std.CountTimer')
        actual = actual_tokens(rt, snk)

        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectSink(self):
        """Testing local connect/disconnect/re-connect on sink"""

        rt, id_ = self.runtime, self.runtime.id

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1)
        request_handler.connect(rt, snk, 'token', id_, src, 'integer')
        time.sleep(0.2)

        request_handler.disconnect(rt, snk)
        request_handler.connect(rt, snk, 'token', id_, src, 'integer')
        time.sleep(0.2)
        request_handler.disconnect(rt, snk)
        # disable(rt, id_, src)

        expected = expected_tokens(rt, src, 'std.CountTimer')
        actual = actual_tokens(rt, snk)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectSource(self):
        """Testing local connect/disconnect/re-connect on source"""

        rt, id_ = self.runtime, self.runtime.id

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1)

        request_handler.connect(rt, snk, "token", id_, src, "integer")
        time.sleep(0.2)
        request_handler.disconnect(rt, src)

        request_handler.connect(rt, snk, "token", id_, src, "integer")
        time.sleep(0.2)
        request_handler.disconnect(rt, src)
        #disable(rt, id_, src)

        expected = expected_tokens(rt, src, "std.CountTimer")
        actual = actual_tokens(rt, snk)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectFilter(self):
        """Testing local connect/disconnect/re-connect on filter"""

        rt, id_ = self.runtime, self.runtime.id

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        sum_ = request_handler.new_actor(rt, "std.Sum", "sum")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1)

        request_handler.connect(rt, snk, "token", id_, sum_, "integer")
        request_handler.connect(rt, sum_, "integer", id_, src, "integer")

        time.sleep(0.2)

        request_handler.disconnect(rt, sum_)

        request_handler.connect(rt, snk, "token", id_, sum_, "integer")
        request_handler.connect(rt, sum_, "integer", id_, src, "integer")

        time.sleep(0.2)

        request_handler.disconnect(rt, src)
        # disable(rt, id_, src)

        expected = expected_tokens(rt, src, "std.Sum")
        actual = actual_tokens(rt, snk)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, sum_)
        request_handler.delete_actor(rt, snk)

    def testTimerLocalSourceSink(self):
        """Testing timer based local source and sink"""

        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist

        src = request_handler.new_actor_wargs(
            rt, 'std.CountTimer', 'src', sleep=0.1, steps=10)
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        request_handler.connect(rt, snk, 'token', id_, src, 'integer')

        time.sleep(1.2)

        # disable(rt, id_, src)
        request_handler.disconnect(rt, src)

        expected = expected_tokens(rt, src, 'std.CountTimer')
        actual = actual_tokens(rt, snk)

        self.assertListPrefix(expected, actual)
        self.assertTrue(len(actual) > 0)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)


@pytest.mark.essential
@pytest.mark.slow
class TestRemoteConnection(CalvinTestBase):

    """Testing remote connections"""

    def testRemoteOneActor(self):
        """Testing remote port"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.5)

        request_handler.disable(rt, src)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testRemoteSlowPort(self):
        """Testing remote slow port and that token flow control works"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        request_handler.connect(rt, snk1, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, alt, 'token_1', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', id_, src2, 'integer')
        time.sleep(2)

        request_handler.disable(rt, src1)
        request_handler.disable(rt, src2)
        time.sleep(0.2)  # HACK

        def _d():
            for i in range(1,100):
                yield i
                yield i

        expected = list(_d())
        actual = actual_tokens(rt, snk1)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(rt, snk1)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

    def testRemoteSlowFanoutPort(self):
        """Testing remote slow port with fan out and that token flow control works"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1)
        snk2 = request_handler.new_actor_wargs(peer, 'io.StandardOut', 'snk2', store_tokens=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        request_handler.connect(rt, snk1, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, snk2, 'token', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_1', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', id_, src2, 'integer')
        time.sleep(2)

        request_handler.disable(rt, src1)
        request_handler.disable(rt, src2)
        time.sleep(0.2)  # HACK

        def _d():
            for i in range(1,100):
                yield i
                yield i

        expected = list(_d())
        actual = actual_tokens(rt, snk1)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        expected = range(1, 100)
        actual = actual_tokens(peer, snk2)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(rt, snk1)
        request_handler.delete_actor(peer, snk2)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

@pytest.mark.essential
@pytest.mark.slow
class TestActorMigration(CalvinTestBase):

    def testOutPortRemoteToLocalMigration(self):
        """Testing outport remote to local migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        request_handler.migrate(rt, src, peer_id)
        time.sleep(0.2)

        expected = expected_tokens(peer, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(peer, src)

    def testFanOutPortLocalToRemoteMigration(self):
        """Testing outport with fan-out local to remote migration"""

        rt = self.runtime
        peer = self.runtimes[0]
        peer_id = peer.id

        src = request_handler.new_actor_wargs(rt, "std.CountTimer", "src", sleep=0.1, steps=100)
        snk_1 = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk-1", store_tokens=1)
        snk_2 = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk-2", store_tokens=1)

        request_handler.set_port_property(rt, src, 'out', 'integer',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(rt, snk_1, 'token', rt.id, src, 'integer')
        request_handler.connect(rt, snk_2, 'token', rt.id, src, 'integer')
        time.sleep(1)

        expected = range(1, 100)
        actual = actual_tokens(rt, snk_1)

        snk_1_start = len(actual)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        actual = actual_tokens(rt, snk_2)
        snk_2_start = len(actual)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        request_handler.migrate(rt, src, peer_id)
        time.sleep(1)

        actual = actual_tokens(rt, snk_1)
        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        assert(len(actual) > snk_1_start + 5)
        self.assertListPrefix(expected, actual)

        actual = actual_tokens(rt, snk_2)
        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        assert(len(actual) > snk_2_start + 5)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(peer, src)
        request_handler.delete_actor(rt, snk_1)
        request_handler.delete_actor(rt, snk_2)

    def testFanOutPortRemoteToLocalMigration(self):
        """Testing outport with fan-out remote to local migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1)
        snk2 = request_handler.new_actor_wargs(peer, 'io.StandardOut', 'snk2', store_tokens=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=0.1, steps=100)

        request_handler.set_port_property(peer, alt, 'out', 'token',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(rt, snk1, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, snk2, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, alt, 'token_1', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', id_, src2, 'integer')
        time.sleep(1)


        def _d():
            for i in range(1,100):
                yield i
                yield i

        expected = list(_d())
        actual = actual_tokens(rt, snk1)
        snk1_0 = len(actual)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        actual = actual_tokens(peer, snk2)
        snk2_0 = len(actual)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        request_handler.migrate(rt, snk1, peer_id)
        time.sleep(1)

        actual = actual_tokens(peer, snk1)
        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        assert(len(actual) > snk1_0 + 5)
        self.assertListPrefix(expected, actual)

        actual = actual_tokens(peer, snk2)
        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        assert(len(actual) > snk2_0 + 5)
        self.assertListPrefix(expected, actual)

        request_handler.delete_actor(peer, snk1)
        request_handler.delete_actor(peer, snk2)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

    def testOutPortLocalToRemoteMigration(self):
        """Testing outport local to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', peer_id, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        request_handler.migrate(peer, src, id_)
        time.sleep(0.2)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and revers repeatedly"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', peer_id, src, 'integer')
        time.sleep(0.27)
        actual_x = []
        actual_1 = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                request_handler.migrate(peer, src, id_)
            else:
                request_handler.migrate(rt, src, peer_id)
            time.sleep(0.2)
            actual_x_ = actual_tokens(rt, snk)
            assert(len(actual_x_) > len(actual_x))
            actual_x = actual_x_

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testInOutPortRemoteToLocalMigration(self):
        """Testing out- and inport remote to local migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        request_handler.migrate(peer, sum_, id_)
        time.sleep(0.2)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(rt, sum_)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and revers repeatedly"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', id_, sum_, 'integer')
        request_handler.connect(rt, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)
        actual_x = []
        actual_1 = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                request_handler.migrate(rt, sum_, peer_id)
            else:
                request_handler.migrate(peer, sum_, id_)
            time.sleep(0.2)
            actual_x_ = actual_tokens(rt, snk)
            assert(len(actual_x_) > len(actual_x))
            actual_x = actual_x_

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalToRemoteMigration(self):
        """Testing out- and inport local to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', id_, sum_, 'integer')
        request_handler.connect(rt, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        request_handler.migrate(rt, sum_, peer_id)
        time.sleep(0.2)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)


    def testInOutPortRemoteToRemoteMigration(self):
        """Testing out- and inport remote to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer0 = self.runtimes[0]
        peer0_id = peer0.id
        peer1 = self.runtimes[1]
        peer1_id = peer1.id

        time.sleep(0.5)
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = request_handler.new_actor(peer0, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer0_id, sum_, 'integer')
        time.sleep(0.5)
        request_handler.connect(peer0, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.5)

        actual_1 = actual_tokens(rt, snk)
        request_handler.migrate(peer0, sum_, peer1_id)
        time.sleep(0.5)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer1, sum_)
        request_handler.delete_actor(rt, src)

    def testExplicitStateMigration(self):
        """Testing migration of explicit state handling"""

        rt = self.runtime
        id_ = rt.id
        peer0 = self.runtimes[0]
        peer0_id = peer0.id
        peer1 = self.runtimes[1]
        peer1_id = peer1.id

        snk = request_handler.new_actor_wargs(peer0, 'io.StandardOut', 'snk', store_tokens=1)
        wrapper = request_handler.new_actor(rt, 'misc.ExplicitStateExample', 'wrapper')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(peer0, snk, 'token', id_, wrapper, 'token')
        request_handler.connect(rt, wrapper, 'token', id_, src, 'integer')
        time.sleep(0.3)

        actual_1 = actual_tokens(peer0, snk)
        request_handler.migrate(rt, wrapper, peer0_id)
        time.sleep(0.3)

        actual = actual_tokens(peer0, snk)
        expected = [u'((( 1 )))', u'((( 2 )))', u'((( 3 )))', u'((( 4 )))', u'((( 5 )))', u'((( 6 )))', u'((( 7 )))', u'((( 8 )))']
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        request_handler.delete_actor(peer0, snk)
        request_handler.delete_actor(peer0, wrapper)
        request_handler.delete_actor(rt, src)


@pytest.mark.essential
@pytest.mark.slow
class TestCalvinScript(CalvinTestBase):

    def testCompileSimple(self):
        rt = self.runtime

        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1)
      src.integer > snk.token
    """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        d.deploy() # ignoring app_id here
        time.sleep(0.5)
        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        request_handler.disconnect(rt, src)

        actual = actual_tokens(rt, snk)
        expected = expected_tokens(rt, src, 'std.CountTimer')

        self.assertListPrefix(expected, actual)

        d.destroy()

    def testDestroyAppWithLocalActors(self):
        rt = self.runtime

        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1)
      src.integer > snk.token
    """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        app_id = d.deploy()
        time.sleep(0.2)
        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        applications = request_handler.get_applications(rt)
        assert app_id in applications

        d.destroy()

        applications = request_handler.get_applications(rt)
        assert app_id not in applications

        actors = request_handler.get_actors(rt)
        assert src not in actors
        assert snk not in actors

    def testDestroyAppWithMigratedActors(self):
        rt = self.runtime
        rt1 = self.runtimes[0]
        rt2 = self.runtimes[1]

        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1)
      src.integer > snk.token
    """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        app_id = d.deploy()
        time.sleep(1.0)
        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        # FIXME --> remove when operating on closed pending connections during migration is fixed
        request_handler.disable(rt, src)
        request_handler.disable(rt, snk)
        # <--
        request_handler.migrate(rt, snk, rt1.id)
        request_handler.migrate(rt, src, rt2.id)

        applications = request_handler.get_applications(rt)
        assert app_id in applications

        d.destroy()

        for retry in range(1, 5):
            applications = request_handler.get_applications(rt)
            if app_id in applications:
                print("Retrying in %s" % (retry * 0.2, ))
                time.sleep(0.2 * retry)
            else :
                break
        assert app_id not in applications

        for retry in range(1, 5):
            actors = []
            actors.extend(request_handler.get_actors(rt))
            actors.extend(request_handler.get_actors(rt1))
            actors.extend(request_handler.get_actors(rt2))
            intersection = [a for a in actors if a in d.actor_map.values()]
            if len(intersection) > 0:
                print("Retrying in %s" % (retry * 0.2, ))
                time.sleep(0.2 * retry)
            else:
                break

        for actor in d.actor_map.values():
            assert actor not in actors
