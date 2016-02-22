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
from calvin.Tools import cscompiler as compiler
from calvin.Tools import deployer
import time
import multiprocessing
from calvin.utilities import calvinconfig
from calvin.utilities import utils
from calvin.utilities.nodecontrol import dispatch_node
from calvin.utilities.attribute_resolver import format_index_string
import pytest
from calvin.utilities import calvinlogger


_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

def actual_tokens(rt, actor_id):
    return utils.report(rt, actor_id)

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
    tokens = utils.report(rt, actor_id)

    if src_actor_type == 'std.CountTimer':
        return expected_counter(tokens)

    if src_actor_type == 'std.Sum':
        return expected_sum(tokens)

    return None

runtime = None
runtimes = []
peerlist = []
kill_peers = True
ip_addr = None


def setup_module(module):
    global runtime
    global runtimes
    global peerlist
    global kill_peers
    global ip_addr
    bt_master_controluri = None

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
            test_peers = utils.get_index(runtime, format_index_string({'node_name':
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
        test_peer2 = utils.get_node(runtime, test_peer2_id)
        if test_peer2:
            runtime2 = utils.RT(test_peer2["control_uri"])
            runtime2.id = test_peer2_id
            runtime2.uri = test_peer2["uri"]
            runtimes.append(runtime2)
        test_peer3_id = test_peers[1]
        if test_peer3_id:
            test_peer3 = utils.get_node(runtime, test_peer3_id)
            if test_peer3:
                runtime3 = utils.RT(test_peer3["control_uri"])
                runtime3.id = test_peer3_id
                runtime3.uri = test_peer3["uri"]
                runtimes.append(runtime3)
    elif bt_master_controluri:
        runtime = utils.RT(bt_master_controluri)
        bt_master_id = utils.get_node_id(runtime)
        data = utils.get_node(runtime, bt_master_id)
        if data:
            runtime.id = bt_master_id
            runtime.uri = data["uri"]
            test_peers = utils.get_nodes(runtime)
            test_peer2_id = test_peers[0]
            test_peer2 = utils.get_node(runtime, test_peer2_id)
            if test_peer2:
                rt2 = utils.RT(test_peer2["control_uri"])
                rt2.id = test_peer2_id
                rt2.uri = test_peer2["uri"]
                runtimes.append(rt2)
            test_peer3_id = test_peers[1]
            if test_peer3_id:
                test_peer3 = utils.get_node(runtime, test_peer3_id)
                if test_peer3:
                    rt3 = utils.RT(test_peer3["control_uri"])
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
        utils.peer_setup(runtime, [i[0] for i in remotehosts])

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
            utils.quit(peer)
            time.sleep(0.2)
    utils.quit(runtime)
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

@pytest.mark.slow
@pytest.mark.essential
class TestNodeSetup(CalvinTestBase):

    """Testing starting a node"""

    def testStartNode(self):
        """Testing starting node"""

        print "### testStartNode ###", self.runtime
        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist
        print "GOT RT"
        assert utils.get_node(rt, id_)['uri'] == rt.uri
        print "GOT URI", rt.uri


@pytest.mark.essential
@pytest.mark.slow
class TestLocalConnectDisconnect(CalvinTestBase):

    """Testing local connect/disconnect/re-connect"""

    def testLocalSourceSink(self):
        """Testing local source and sink"""

        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist

        src = utils.new_actor(rt, 'std.CountTimer', 'src')
        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        utils.connect(rt, snk, 'token', id_, src, 'integer')

        time.sleep(0.4)

        # disable(rt, id_, src)
        utils.disconnect(rt, src)

        expected = expected_tokens(rt, src, 'std.CountTimer')
        actual = actual_tokens(rt, snk)

        self.assertListPrefix(expected, actual)

        utils.delete_actor(rt, src)
        utils.delete_actor(rt, snk)

    def testLocalConnectDisconnectSink(self):
        """Testing local connect/disconnect/re-connect on sink"""

        rt, id_ = self.runtime, self.runtime.id

        src = utils.new_actor(rt, "std.CountTimer", "src")
        snk = utils.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1)
        utils.connect(rt, snk, 'token', id_, src, 'integer')
        time.sleep(0.2)

        utils.disconnect(rt, snk)
        utils.connect(rt, snk, 'token', id_, src, 'integer')
        time.sleep(0.2)
        utils.disconnect(rt, snk)
        # disable(rt, id_, src)

        expected = expected_tokens(rt, src, 'std.CountTimer')
        actual = actual_tokens(rt, snk)
        self.assertListPrefix(expected, actual)

        utils.delete_actor(rt, src)
        utils.delete_actor(rt, snk)

    def testLocalConnectDisconnectSource(self):
        """Testing local connect/disconnect/re-connect on source"""

        rt, id_ = self.runtime, self.runtime.id

        src = utils.new_actor(rt, "std.CountTimer", "src")
        snk = utils.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1)

        utils.connect(rt, snk, "token", id_, src, "integer")
        time.sleep(0.2)
        utils.disconnect(rt, src)

        utils.connect(rt, snk, "token", id_, src, "integer")
        time.sleep(0.2)
        utils.disconnect(rt, src)
        #disable(rt, id_, src)

        expected = expected_tokens(rt, src, "std.CountTimer")
        actual = actual_tokens(rt, snk)
        self.assertListPrefix(expected, actual)

        utils.delete_actor(rt, src)
        utils.delete_actor(rt, snk)

    def testLocalConnectDisconnectFilter(self):
        """Testing local connect/disconnect/re-connect on filter"""

        rt, id_ = self.runtime, self.runtime.id

        src = utils.new_actor(rt, "std.CountTimer", "src")
        sum_ = utils.new_actor(rt, "std.Sum", "sum")
        snk = utils.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1)

        utils.connect(rt, snk, "token", id_, sum_, "integer")
        utils.connect(rt, sum_, "integer", id_, src, "integer")

        time.sleep(0.2)

        utils.disconnect(rt, sum_)

        utils.connect(rt, snk, "token", id_, sum_, "integer")
        utils.connect(rt, sum_, "integer", id_, src, "integer")

        time.sleep(0.2)

        utils.disconnect(rt, src)
        # disable(rt, id_, src)

        expected = expected_tokens(rt, src, "std.Sum")
        actual = actual_tokens(rt, snk)
        self.assertListPrefix(expected, actual)

        utils.delete_actor(rt, src)
        utils.delete_actor(rt, sum_)
        utils.delete_actor(rt, snk)

    def testTimerLocalSourceSink(self):
        """Testing timer based local source and sink"""

        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist

        src = utils.new_actor_wargs(
            rt, 'std.CountTimer', 'src', sleep=0.1, steps=10)
        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        utils.connect(rt, snk, 'token', id_, src, 'integer')

        time.sleep(1.2)

        # disable(rt, id_, src)
        utils.disconnect(rt, src)

        expected = expected_tokens(rt, src, 'std.CountTimer')
        actual = actual_tokens(rt, snk)

        self.assertListPrefix(expected, actual)
        self.assertTrue(len(actual) > 0)

        utils.delete_actor(rt, src)
        utils.delete_actor(rt, snk)


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

        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(peer, 'std.Sum', 'sum')
        src = utils.new_actor(rt, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        utils.connect(peer, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.5)

        utils.disable(rt, src)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        utils.delete_actor(rt, snk)
        utils.delete_actor(peer, sum_)
        utils.delete_actor(rt, src)

    def testRemoteSlowPort(self):
        """Testing remote slow port and that token flow control works"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1)
        alt = utils.new_actor(peer, 'std.Alternate', 'alt')
        src1 = utils.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = utils.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        utils.connect(rt, snk1, 'token', peer_id, alt, 'token')
        utils.connect(peer, alt, 'token_1', id_, src1, 'integer')
        utils.connect(peer, alt, 'token_2', id_, src2, 'integer')
        time.sleep(2)

        utils.disable(rt, src1)
        utils.disable(rt, src2)
        time.sleep(0.2)  # HACK

        def _d():
            for i in range(1,100):
                yield i
                yield i

        expected = list(_d())
        actual = actual_tokens(rt, snk1)
        assert(len(actual) > 1)
        self.assertListPrefix(expected, actual)

        utils.delete_actor(rt, snk1)
        utils.delete_actor(peer, alt)
        utils.delete_actor(rt, src1)
        utils.delete_actor(rt, src2)

    def testRemoteSlowFanoutPort(self):
        """Testing remote slow port with fan out and that token flow control works"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1)
        snk2 = utils.new_actor_wargs(peer, 'io.StandardOut', 'snk2', store_tokens=1)
        alt = utils.new_actor(peer, 'std.Alternate', 'alt')
        src1 = utils.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = utils.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        utils.connect(rt, snk1, 'token', peer_id, alt, 'token')
        utils.connect(peer, snk2, 'token', id_, src1, 'integer')
        utils.connect(peer, alt, 'token_1', id_, src1, 'integer')
        utils.connect(peer, alt, 'token_2', id_, src2, 'integer')
        time.sleep(2)

        utils.disable(rt, src1)
        utils.disable(rt, src2)
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

        utils.delete_actor(rt, snk1)
        utils.delete_actor(peer, snk2)
        utils.delete_actor(peer, alt)
        utils.delete_actor(rt, src1)
        utils.delete_actor(rt, src2)

@pytest.mark.essential
@pytest.mark.slow
class TestActorMigration(CalvinTestBase):

    def testOutPortRemoteToLocalMigration(self):
        """Testing outport remote to local migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(peer, 'std.Sum', 'sum')
        src = utils.new_actor(rt, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        utils.connect(peer, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        utils.migrate(rt, src, peer_id)
        time.sleep(0.2)

        expected = expected_tokens(peer, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(rt, snk)
        utils.delete_actor(peer, sum_)
        utils.delete_actor(peer, src)

    def testOutPortLocalToRemoteMigration(self):
        """Testing outport local to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(peer, 'std.Sum', 'sum')
        src = utils.new_actor(peer, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        utils.connect(peer, sum_, 'integer', peer_id, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        utils.migrate(peer, src, id_)
        time.sleep(0.2)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(rt, snk)
        utils.delete_actor(peer, sum_)
        utils.delete_actor(rt, src)

    def testOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and revers repeatedly"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(peer, 'std.Sum', 'sum')
        src = utils.new_actor(peer, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        utils.connect(peer, sum_, 'integer', peer_id, src, 'integer')
        time.sleep(0.27)
        actual_x = []
        actual_1 = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                utils.migrate(peer, src, id_)
            else:
                utils.migrate(rt, src, peer_id)
            time.sleep(0.2)
            actual_x_ = actual_tokens(rt, snk)
            assert(len(actual_x_) > len(actual_x))
            actual_x = actual_x_

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(rt, snk)
        utils.delete_actor(peer, sum_)
        utils.delete_actor(rt, src)

    def testInOutPortRemoteToLocalMigration(self):
        """Testing out- and inport remote to local migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(peer, 'std.Sum', 'sum')
        src = utils.new_actor(rt, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        utils.connect(peer, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        utils.migrate(peer, sum_, id_)
        time.sleep(0.2)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(rt, snk)
        utils.delete_actor(rt, sum_)
        utils.delete_actor(rt, src)

    def testInOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and revers repeatedly"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(rt, 'std.Sum', 'sum')
        src = utils.new_actor(rt, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', id_, sum_, 'integer')
        utils.connect(rt, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)
        actual_x = []
        actual_1 = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                utils.migrate(rt, sum_, peer_id)
            else:
                utils.migrate(peer, sum_, id_)
            time.sleep(0.2)
            actual_x_ = actual_tokens(rt, snk)
            assert(len(actual_x_) > len(actual_x))
            actual_x = actual_x_

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(rt, snk)
        utils.delete_actor(peer, sum_)
        utils.delete_actor(rt, src)

    def testInOutPortLocalToRemoteMigration(self):
        """Testing out- and inport local to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(rt, 'std.Sum', 'sum')
        src = utils.new_actor(rt, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', id_, sum_, 'integer')
        utils.connect(rt, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.27)

        actual_1 = actual_tokens(rt, snk)
        utils.migrate(rt, sum_, peer_id)
        time.sleep(0.2)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(rt, snk)
        utils.delete_actor(peer, sum_)
        utils.delete_actor(rt, src)


    def testInOutPortRemoteToRemoteMigration(self):
        """Testing out- and inport remote to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer0 = self.runtimes[0]
        peer0_id = peer0.id
        peer1 = self.runtimes[1]
        peer1_id = peer1.id

        time.sleep(0.5)
        snk = utils.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1)
        sum_ = utils.new_actor(peer0, 'std.Sum', 'sum')
        src = utils.new_actor(rt, 'std.CountTimer', 'src')

        utils.connect(rt, snk, 'token', peer0_id, sum_, 'integer')
        time.sleep(0.5)
        utils.connect(peer0, sum_, 'integer', id_, src, 'integer')
        time.sleep(0.5)

        actual_1 = actual_tokens(rt, snk)
        utils.migrate(peer0, sum_, peer1_id)
        time.sleep(0.5)

        expected = expected_tokens(rt, src, 'std.Sum')
        actual = actual_tokens(rt, snk)
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(rt, snk)
        utils.delete_actor(peer1, sum_)
        utils.delete_actor(rt, src)

    def testExplicitStateMigration(self):
        """Testing migration of explicit state handling"""

        rt = self.runtime
        id_ = rt.id
        peer0 = self.runtimes[0]
        peer0_id = peer0.id
        peer1 = self.runtimes[1]
        peer1_id = peer1.id

        snk = utils.new_actor_wargs(peer0, 'io.StandardOut', 'snk', store_tokens=1)
        wrapper = utils.new_actor(rt, 'misc.ExplicitStateExample', 'wrapper')
        src = utils.new_actor(rt, 'std.CountTimer', 'src')

        utils.connect(peer0, snk, 'token', id_, wrapper, 'token')
        utils.connect(rt, wrapper, 'token', id_, src, 'integer')
        time.sleep(0.3)

        actual_1 = actual_tokens(peer0, snk)
        utils.migrate(rt, wrapper, peer0_id)
        time.sleep(0.3)

        actual = actual_tokens(peer0, snk)
        expected = [u'((( 1 )))', u'((( 2 )))', u'((( 3 )))', u'((( 4 )))', u'((( 5 )))', u'((( 6 )))', u'((( 7 )))', u'((( 8 )))']
        assert(len(actual) > 1)
        assert(len(actual) > len(actual_1))
        self.assertListPrefix(expected, actual)
        utils.delete_actor(peer0, snk)
        utils.delete_actor(peer0, wrapper)
        utils.delete_actor(rt, src)


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
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(rt, app_info)
        d.deploy() # ignoring app_id here
        time.sleep(0.5)
        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        utils.disconnect(rt, src)

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
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(rt, app_info)
        app_id = d.deploy()
        time.sleep(0.2)
        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        applications = utils.get_applications(rt)
        assert app_id in applications

        d.destroy()

        applications = utils.get_applications(rt)
        assert app_id not in applications

        actors = utils.get_actors(rt)
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
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(rt, app_info)
        app_id = d.deploy()
        time.sleep(1.0)
        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        # FIXME --> remove when operating on closed pending connections during migration is fixed
        utils.disable(rt, src)
        utils.disable(rt, snk)
        # <--
        utils.migrate(rt, snk, rt1.id)
        utils.migrate(rt, src, rt2.id)

        applications = utils.get_applications(rt)
        assert app_id in applications

        d.destroy()

        for retry in range(1, 5):
            applications = utils.get_applications(rt)
            if app_id in applications:
                print("Retrying in %s" % (retry * 0.2, ))
                time.sleep(0.2 * retry)
            else :
                break
        assert app_id not in applications

        for retry in range(1, 5):
            actors = []
            actors.extend(utils.get_actors(rt))
            actors.extend(utils.get_actors(rt1))
            actors.extend(utils.get_actors(rt2))
            intersection = [a for a in actors if a in d.actor_map.values()]
            if len(intersection) > 0:
                print("Retrying in %s" % (retry * 0.2, ))
                time.sleep(0.2 * retry)
            else:
                break

        for actor in d.actor_map.values():
            assert actor not in actors


@pytest.mark.essential
@pytest.mark.slow
class TestPeerSetup(CalvinTestBase):

    def testPeerSetup(self):
        global ip_addr
        rt1, _ = dispatch_node(["calvinip://%s:5010" % (ip_addr, )], "http://localhost:5011")
        rt2, _ = dispatch_node(["calvinip://%s:5012" % (ip_addr, )], "http://localhost:5013")
        rt3, _ = dispatch_node(["calvinip://%s:5014" % (ip_addr, )], "http://localhost:5015")

        peers = [rt2.uri[0], rt3.uri[0]]
        utils.peer_setup(rt1, peers)

        time.sleep(0.5)

        rt1_nodes = utils.get_nodes(rt1)
        rt2_nodes = utils.get_nodes(rt2)
        rt3_nodes = utils.get_nodes(rt3)

        for peer in [rt1, rt2, rt3]:
            utils.quit(peer)
            time.sleep(0.2)

        assert rt2.id in rt1_nodes
        assert rt3.id in rt1_nodes

        assert rt1.id in rt2_nodes
        assert rt3.id in rt2_nodes

        assert rt1.id in rt3_nodes
        assert rt2.id in rt3_nodes
