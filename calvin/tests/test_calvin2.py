# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Ericsson AB
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
from calvin.Tools import cscompiler as compile_tool
from calvin.Tools import deployer
from calvin.utilities import calvinlogger
from calvin.utilities.nodecontrol import dispatch_node
from calvin.utilities.attribute_resolver import format_index_string
from calvin.requests.request_handler import RequestHandler, RT

_log = calvinlogger.get_logger(__name__)


def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)

rt1 = None
rt2 = None
rt3 = None
kill_peers = True
request_handler = None


def setup_module(module):
    global rt1
    global rt2
    global rt3
    global kill_peers
    global request_handler

    ip_addr = None
    bt_master_controluri = None
    request_handler = RequestHandler()

    try:
        ip_addr = os.environ["CALVIN_TEST_IP"]
        purpose = os.environ["CALVIN_TEST_UUID"]
        _log.debug("Running remote tests")
    except KeyError:
        _log.debug("Running local test")
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

        rt1,_ = dispatch_node(["calvinip://%s:%s" % (ip_addr, ports[0])], "http://%s:%s" % (ip_addr, ports[1]))

        _log.debug("First runtime started, control http://%s:%s, calvinip://%s:%s" % (ip_addr, ports[1], ip_addr, ports[0]))

        interval = 0.5
        for retries in range(1,20):
            time.sleep(interval)
            _log.debug("Trying to get test nodes for 'purpose' %s" % purpose)
            test_peers = request_handler.get_index(rt1, format_index_string({'node_name':
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

        _log.debug("All remote nodes found!")

        test_peer2_id = test_peers[0]
        test_peer2 = request_handler.get_node(rt1, test_peer2_id)
        if test_peer2:
            rt2 = RT(test_peer2["control_uri"])
            rt2.id = test_peer2_id
            rt2.uri = test_peer2["uri"]
        test_peer3_id = test_peers[1]
        if test_peer3_id:
            test_peer3 = request_handler.get_node(rt1, test_peer3_id)
            if test_peer3:
                rt3 = RT(test_peer3["control_uri"])
                rt3.id = test_peer3_id
                rt3.uri = test_peer3["uri"]
    elif bt_master_controluri:
        rt1 = RT(bt_master_controluri)
        bt_master_id = request_handler.get_node_id(rt1)
        data = request_handler.get_node(rt1, bt_master_id)
        if data:
            rt1.id = bt_master_id
            rt1.uri = data["uri"]
            test_peers = request_handler.get_nodes(rt1)
            test_peer2_id = test_peers[0]
            test_peer2 = request_handler.get_node(rt1, test_peer2_id)
            if test_peer2:
                rt2 = RT(test_peer2["control_uri"])
                rt2.id = test_peer2_id
                rt2.uri = test_peer2["uri"]
            test_peer3_id = test_peers[1]
            if test_peer3_id:
                test_peer3 = request_handler.get_node(rt1, test_peer3_id)
                if test_peer3:
                    rt3 = RT(test_peer3["control_uri"])
                    rt3.id = test_peer3_id
                    rt3.uri = test_peer3["uri"]
    else:
        try:
            ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
        except:
            import socket
            ip_addr = socket.gethostbyname(socket.gethostname())
        rt1,_ = dispatch_node(["calvinip://%s:5000" % (ip_addr,)], "http://localhost:5003")
        rt2,_ = dispatch_node(["calvinip://%s:5001" % (ip_addr,)], "http://localhost:5004")
        rt3,_ = dispatch_node(["calvinip://%s:5002" % (ip_addr,)], "http://localhost:5005")
        time.sleep(.4)
        request_handler.peer_setup(rt1, ["calvinip://%s:5001" % (ip_addr,), "calvinip://%s:5002" % (ip_addr, )])
        request_handler.peer_setup(rt2, ["calvinip://%s:5000" % (ip_addr,), "calvinip://%s:5002" % (ip_addr, )])
        request_handler.peer_setup(rt3, ["calvinip://%s:5000" % (ip_addr,), "calvinip://%s:5001" % (ip_addr, )])
        time.sleep(.4)


def teardown_module(module):
    global rt1
    global rt2
    global rt3
    global kill_peers

    request_handler.quit(rt1)
    if kill_peers:
        request_handler.quit(rt2)
        request_handler.quit(rt3)
    time.sleep(0.4)
    for p in multiprocessing.active_children():
        p.terminate()
    time.sleep(0.4)

class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.rt1 = rt1
        self.rt2 = rt2
        self.rt3 = rt3

    def assert_lists_equal(self, expected, actual, min_length=5):
        self.assertTrue(len(actual) >= min_length, "Received data too short (%d), need at least %d" % (len(actual), min_length))
        l = min([len(expected), len(actual)])
        self.assertListEqual(expected[:l], actual[:l])

    def compile_script(self, script, name):
        # Instead of rewriting tests after compiler.compile_script changed
        # from returning app_info, errors, warnings to app_info, issuetracker
        # use this stub in tests to keep old behaviour
        app_info, issuetracker = compiler.compile_script(script, name)
        return app_info, issuetracker.errors(), issuetracker.warnings()


@pytest.mark.essential
class TestConnections(CalvinTestBase):

    @pytest.mark.slow
    def testLocalSourceSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(.5)

        actual = request_handler.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk)

    def testMigrateSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(.4)
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(.6)

        actual = request_handler.report(self.rt2, snk)
        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt2, snk)

    def testMigrateSource(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(1)
        request_handler.migrate(self.rt1, src, self.rt2.id)

        interval = 0.5
        for retries in range(1,5):
            time.sleep(interval * retries)
            actual = request_handler.report(self.rt1, snk)
            if len(actual) > 10 :
                break


        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt2, src)
        request_handler.delete_actor(self.rt1, snk)

    def testTwoStepMigrateSinkSource(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(1)
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(1)
        request_handler.migrate(self.rt1, src, self.rt2.id)
        time.sleep(1)

        actual = request_handler.report(self.rt2, snk)
        self.assert_lists_equal(range(1,15), actual, min_length=10)

        request_handler.delete_actor(self.rt2, src)
        request_handler.delete_actor(self.rt2, snk)

    def testTwoStepMigrateSourceSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(1)
        request_handler.migrate(self.rt1, src, self.rt2.id)
        request_handler.report(self.rt1, snk)
        time.sleep(1)
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(1)

        actual = request_handler.report(self.rt2, snk)
        self.assert_lists_equal(range(1,20), actual, min_length=15)

        request_handler.delete_actor(self.rt2, src)
        request_handler.delete_actor(self.rt2, snk)


@pytest.mark.essential
class TestScripts(CalvinTestBase):

    @pytest.mark.slow
    def testInlineScript(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        snk = d.actor_map['simple:snk']

        actual = request_handler.report(self.rt1, (snk))
        self.assert_lists_equal(range(1, 20), actual)

        d.destroy()

    @pytest.mark.slow
    def testFileScript(self):
        _log.analyze("TESTRUN", "+", {})
        scriptname = 'test1'
        scriptfile = absolute_filename("scripts/%s.calvin" % (scriptname, ))
        app_info, issuetracker = compile_tool.compile_file(scriptfile)
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        src = d.actor_map['%s:src' % scriptname]
        snk = d.actor_map['%s:snk' % scriptname]

        actual = request_handler.report(self.rt1, snk)
        self.assert_lists_equal(range(1, 20), actual)

        d.destroy()


@pytest.mark.essential
class TestMetering(CalvinTestBase):

    @pytest.mark.slow
    def testMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        r = request_handler.register_metering(self.rt1)
        user_id = r['user_id']
        metering_timeout = r['timeout']
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)
        metainfo = request_handler.get_actorinfo_metering(self.rt1, user_id)
        data1 = request_handler.get_timed_metering(self.rt1, user_id)
        time.sleep(0.5)
        data2 = request_handler.get_timed_metering(self.rt1, user_id)
        snk = d.actor_map['simple:snk']
        assert snk in metainfo
        assert data1[snk][0][1] in metainfo[snk]
        actual = request_handler.report(self.rt1, (snk))
        self.assert_lists_equal(range(1, 20), actual)
        # Verify only new data
        assert max([data[0] for data in data1[snk]]) < min([data[0] for data in data2[snk]])
        # Verify about same number of tokens (time diff makes exact match not possible)
        diff = len(data1[snk]) + len(data2[snk]) - len(actual)
        assert diff > -3 and diff < 3
        request_handler.unregister_metering(self.rt1, user_id)
        d.destroy()

    @pytest.mark.slow
    def testMigratingMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        r1 = request_handler.register_metering(self.rt1)
        user_id = r1['user_id']
        # Register as same user to keep it simple
        r2 = request_handler.register_metering(self.rt2, user_id)
        # deploy app
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        # migrate sink back and forth
        time.sleep(0.5)
        snk = d.actor_map['simple:snk']
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(0.5)
        request_handler.migrate(self.rt2, snk, self.rt1.id)
        time.sleep(0.5)
        # Get metering
        metainfo1 = request_handler.get_actorinfo_metering(self.rt1, user_id)
        metainfo2 = request_handler.get_actorinfo_metering(self.rt2, user_id)
        data1 = request_handler.get_timed_metering(self.rt1, user_id)
        data2 = request_handler.get_timed_metering(self.rt2, user_id)
        # Check metainfo
        assert snk in metainfo1
        assert snk in metainfo2
        assert data1[snk][0][1] in metainfo1[snk]
        assert data2[snk][0][1] in metainfo2[snk]
        # Check that the sink produced something
        actual = request_handler.report(self.rt1, (snk))
        self.assert_lists_equal(range(1, 20), actual)
        # Verify action times of data2 is in middle of data1
        limits = (min([data[0] for data in data2[snk]]), max([data[0] for data in data2[snk]]))
        v = [data[0] for data in data1[snk]]
        assert len(filter(lambda x: x > limits[0] and x < limits[1], v)) == 0
        assert len(filter(lambda x: x < limits[0], v)) > 0
        assert len(filter(lambda x: x > limits[1], v)) > 0
        # Verify about same number of tokens (time diff makes exact match not possible)
        diff = len(data1[snk]) + len(data2[snk]) - len(actual)
        assert diff > -3 and diff < 3
        request_handler.unregister_metering(self.rt1, user_id)
        request_handler.unregister_metering(self.rt2, user_id)
        d.destroy()

    @pytest.mark.slow
    def testAggregatedMigratingMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        r1 = request_handler.register_metering(self.rt1)
        user_id = r1['user_id']
        # Register as same user to keep it simple
        r2 = request_handler.register_metering(self.rt2, user_id)
        # deploy app
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        # migrate sink back and forth
        time.sleep(0.5)
        snk = d.actor_map['simple:snk']
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(0.5)
        request_handler.migrate(self.rt2, snk, self.rt1.id)
        time.sleep(0.5)
        # Get metering
        metainfo1 = request_handler.get_actorinfo_metering(self.rt1, user_id)
        data1 = request_handler.get_timed_metering(self.rt1, user_id)
        agg2 = request_handler.get_aggregated_metering(self.rt2, user_id)
        data2 = request_handler.get_timed_metering(self.rt2, user_id)
        agg1 = request_handler.get_aggregated_metering(self.rt1, user_id)
        metainfo2 = request_handler.get_actorinfo_metering(self.rt2, user_id)
        # Check metainfo
        assert snk in metainfo1
        assert snk in metainfo2
        assert data1[snk][0][1] in metainfo1[snk]
        assert data2[snk][0][1] in metainfo2[snk]
        # Check that the sink produced something
        actual = request_handler.report(self.rt1, (snk))
        self.assert_lists_equal(range(1, 20), actual)
        # Verify about same number of tokens (time diff makes exact match not possible)
        total_timed = len(data1[snk]) + len(data2[snk])
        diff = total_timed - len(actual)
        assert diff > -3 and diff < 3
        total_agg = sum(agg1['activity'][snk].values()) + sum(agg2['activity'][snk].values())
        diff = total_agg - len(actual)
        assert diff > -3 and diff < 3
        assert sum(agg1['activity'][snk].values()) >= len(data1[snk])
        assert sum(agg2['activity'][snk].values()) <= len(data2[snk])
        request_handler.unregister_metering(self.rt1, user_id)
        request_handler.unregister_metering(self.rt2, user_id)
        d.destroy()


    @pytest.mark.slow
    def testLateAggregatedMigratingMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        # deploy app
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        # migrate sink back and forth
        time.sleep(0.5)
        snk = d.actor_map['simple:snk']
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(0.5)
        request_handler.migrate(self.rt2, snk, self.rt1.id)
        time.sleep(0.5)
        # Metering
        r1 = request_handler.register_metering(self.rt1)
        user_id = r1['user_id']
        # Register as same user to keep it simple
        r2 = request_handler.register_metering(self.rt2, user_id)
        metainfo1 = request_handler.get_actorinfo_metering(self.rt1, user_id)
        agg2 = request_handler.get_aggregated_metering(self.rt2, user_id)
        agg1 = request_handler.get_aggregated_metering(self.rt1, user_id)
        metainfo2 = request_handler.get_actorinfo_metering(self.rt2, user_id)
        # Check metainfo
        assert snk in metainfo1
        assert snk in metainfo2
        # Check that the sink produced something
        actual = request_handler.report(self.rt1, (snk))
        self.assert_lists_equal(range(1, 20), actual)
        total_agg = sum(agg1['activity'][snk].values()) + sum(agg2['activity'][snk].values())
        diff = total_agg - len(actual)
        assert diff > -3 and diff < 3
        request_handler.unregister_metering(self.rt1, user_id)
        request_handler.unregister_metering(self.rt2, user_id)
        d.destroy()


class TestStateMigration(CalvinTestBase):

    def testSimpleState(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        request_handler.migrate(self.rt1, csum, self.rt2.id)
        time.sleep(1)

        actual = request_handler.report(self.rt1, snk)
        expected = [sum(range(i+1)) for i in range(1,10)]

        self.assert_lists_equal(expected, actual)

        d.destroy()


@pytest.mark.slow
@pytest.mark.essential
class TestAppLifeCycle(CalvinTestBase):

    def testAppDestructionOneRemote(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        request_handler.migrate(self.rt1, csum, self.rt2.id)
        time.sleep(.5)

        actual = request_handler.report(self.rt1, snk)
        expected = [sum(range(i+1)) for i in range(1,10)]
        self.assert_lists_equal(expected, actual)
        request_handler.delete_application(self.rt1, d.app_id)

        for a in range(0, 20):
            all_removed = None
            try:
                self.assertFalse(request_handler.get_actor(self.rt1, src))
                self.assertFalse(request_handler.get_actor(self.rt1, csum))
                self.assertFalse(request_handler.get_actor(self.rt1, snk))
                self.assertFalse(request_handler.get_actor(self.rt2, src))
                self.assertFalse(request_handler.get_actor(self.rt2, csum))
                self.assertFalse(request_handler.get_actor(self.rt2, snk))
                self.assertFalse(request_handler.get_actor(self.rt3, src))
                self.assertFalse(request_handler.get_actor(self.rt3, csum))
                self.assertFalse(request_handler.get_actor(self.rt3, snk))
            except AssertionError as e:
                print a, e
                all_removed = e
            if all_removed is None:
                break
            time.sleep(1)

        if all_removed:
            raise all_removed

        self.assertFalse(request_handler.get_application(self.rt1, d.app_id))
        self.assertFalse(request_handler.get_application(self.rt2, d.app_id))
        self.assertFalse(request_handler.get_application(self.rt3, d.app_id))

    def testAppDestructionAllRemote(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        import sys
        from twisted.python import log
        log.startLogging(sys.stdout)

        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.2)
        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        request_handler.migrate(self.rt1, src, self.rt2.id)
        request_handler.migrate(self.rt1, csum, self.rt2.id)
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(.5)

        actual = request_handler.report(self.rt2, snk)
        expected = [sum(range(i+1)) for i in range(1,10)]
        self.assert_lists_equal(expected, actual)
        request_handler.delete_application(self.rt1, d.app_id)

        for a in range(20):
            all_removed = None
            try:
                self.assertFalse(request_handler.get_actor(self.rt1, csum))
                self.assertFalse(request_handler.get_actor(self.rt1, snk))
                self.assertFalse(request_handler.get_actor(self.rt2, src))
                self.assertFalse(request_handler.get_actor(self.rt2, csum))
                self.assertFalse(request_handler.get_actor(self.rt2, snk))
                self.assertFalse(request_handler.get_actor(self.rt3, src))
                self.assertFalse(request_handler.get_actor(self.rt3, csum))
                self.assertFalse(request_handler.get_actor(self.rt3, snk))
            except AssertionError as e:
                print a, e
                all_removed = e
            if all_removed is None:
                break
            time.sleep(1)

        if all_removed:
            raise all_removed

        self.assertFalse(request_handler.get_application(self.rt1, d.app_id))
        self.assertFalse(request_handler.get_application(self.rt2, d.app_id))
        self.assertFalse(request_handler.get_application(self.rt3, d.app_id))


@pytest.mark.essential
class TestEnabledToEnabledBug(CalvinTestBase):

    def test10(self):
        _log.analyze("TESTRUN", "+", {})
        # Two actors, doesn't seem to trigger the bug
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(0.1)

        actual = request_handler.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk)

    def test11(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test10, but scripted
        script = """
            src : std.Counter()
            snk : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.06)

        snk = d.actor_map['simple:snk']
        actual = request_handler.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

        d.destroy()

    def test20(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt1, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, ity, 'token')
        request_handler.connect(self.rt1, ity, 'token', self.rt1.id, src, 'integer')

        time.sleep(0.2)

        actual = request_handler.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 11), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, ity)
        request_handler.delete_actor(self.rt1, snk)

    def test21(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt2, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt3, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt3, snk, 'token', self.rt2.id, ity, 'token')
        request_handler.connect(self.rt2, ity, 'token', self.rt1.id, src, 'integer')

        interval = 0.5

        for retries in range(1, 5):
            time.sleep(retries * interval)
            actual = request_handler.report(self.rt3, snk)
            if len(actual) > 10:
                break

        while len(actual) < 10:
            time.sleep(0.1)
            actual = request_handler.report(self.rt3, snk)

        self.assert_lists_equal(range(1, 11), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt2, ity)
        request_handler.delete_actor(self.rt3, snk)

    def test22(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt2, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt3, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt2, ity, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt3, snk, 'token', self.rt2.id, ity, 'token')

        interval = 0.5

        for retries in range(1, 5):
            time.sleep(retries * interval)
            actual = request_handler.report(self.rt3, snk)
            if len(actual) > 10:
                break

        self.assert_lists_equal(range(1, 11), actual)

        time.sleep(0.1)

        actual = request_handler.report(self.rt3, snk)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt2, ity)
        request_handler.delete_actor(self.rt3, snk)

    def test25(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt1, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, ity, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, ity, 'token')

        time.sleep(0.2)

        actual = request_handler.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, ity)
        request_handler.delete_actor(self.rt1, snk)

    def test26(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test20
        script = """
            src : std.Counter()
            ity : std.Identity()
            snk : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > ity.token
            ity.token > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.4)

        snk = d.actor_map['simple:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        d.destroy()

    def test30(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(self.rt1, src, 'out', 'integer',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(self.rt1, snk1, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt1, snk2, 'token', self.rt1.id, src, 'integer')

        time.sleep(0.2)

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        self.assert_lists_equal(list(range(1, 10)), actual1)
        self.assert_lists_equal(list(range(1, 10)), actual2)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk1)
        request_handler.delete_actor(self.rt1, snk2)

    def test31(self):
        # Verify that fanout defined implicitly in scripts is handled correctly
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            snk2 : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test31")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.1)

        snk1 = d.actor_map['test31:snk1']
        snk2 = d.actor_map['test31:snk2']
        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)

        d.destroy()

    def test32(self):
        # Verify that fanout from component inports is handled correctly
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Foo() in -> a, b{
              a : std.Identity()
              b : std.Identity()
              .in >  a.token
              .in > b.token
              a.token > .a
              b.token > .b
            }

            snk2 : io.StandardOut(store_tokens=1, quiet=1)
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            foo : Foo()
            req : std.Counter()
            req.integer > foo.in
            foo.a > snk1.token
            foo.b > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test32")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.1)

        snk1 = d.actor_map['test32:snk1']
        snk2 = d.actor_map['test32:snk2']
        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)

        d.destroy()

    def test40(self):
        # Verify round robin port
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(self.rt1, src, 'out', 'integer',
                                            port_properties={'routing': 'round-robin', 'nbr_peers': 2})

        request_handler.connect(self.rt1, snk1, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt1, snk2, 'token', self.rt1.id, src, 'integer')

        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        time.sleep(1.0)

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk1)
        request_handler.delete_actor(self.rt1, snk2)



@pytest.mark.essential
class TestNullPorts(CalvinTestBase):

    def testVoidActor(self):
        # Verify that the null port of a std.Void actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src1 : std.Counter()
            src2 : std.Void()
            join : std.Join()
            snk  : io.StandardOut(store_tokens=1, quiet=1)

            src1.integer > join.token_1
            src2.void > join.token_2
            join.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testVoidActor")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.4)

        snk = d.actor_map['testVoidActor:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        d.destroy()

    def testTerminatorActor(self):
        # Verify that the null port of a std.Terminator actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src  : std.Counter()
            term : std.Terminator()
            snk  : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > term.void
            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testTerminatorActor")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testTerminatorActor:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        d.destroy()

@pytest.mark.essential
class TestCompare(CalvinTestBase):

    def testBadOp(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op="<>")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadOp")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.05)

        snk = d.actor_map['testBadOp:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [0] * 10

        self.assert_lists_equal(expected, actual)

        d.destroy()

    def testEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op="=")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testEqual")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.1)

        snk = d.actor_map['testEqual:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [x == 5 for x in range(1, 10)]

        self.assert_lists_equal(expected, actual)

        d.destroy()

    def testGreaterThanOrEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op=">=")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testGreaterThanOrEqual")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.1)

        snk = d.actor_map['testGreaterThanOrEqual:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [x >= 5 for x in range(1, 10)]

        self.assert_lists_equal(expected, actual)

        d.destroy()


@pytest.mark.essential
class TestSelect(CalvinTestBase):

    def testTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=true, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > snk.token
            route.case_false > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testTrue")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.2)

        snk = d.actor_map['testTrue:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        d.destroy()

    def testFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=0, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testFalse")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testFalse:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        d.destroy()

    def testBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=2, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadSelect")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testBadSelect:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        d.destroy()


@pytest.mark.essential
class TestDeselect(CalvinTestBase):

    def testDeselectTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=-1)
            const_1 : std.Constant(data=1, n=-1)
            comp    : std.Compare(op="<=")
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.case_false
            const_1.token > ds.case_true
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectTrue")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testDeselectTrue:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [1] * 5 + [0] * 5

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testDeselectFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=-1)
            const_1 : std.Constant(data=1, n=-1)
            comp    : std.Compare(op="<=")
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.case_true
            const_1.token > ds.case_false
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectFalse")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testDeselectFalse:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [0] * 5 + [1] * 5

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testDeselectBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=11)
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.case_false
            src.integer > ds.case_true
            const_0.token > const_5.in
            const_5.out > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectBadSelect")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testDeselectBadSelect:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [0] * 10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()


@pytest.mark.essential
class TestLineJoin(CalvinTestBase):

    def testBasicJoin(self):
        _log.analyze("TESTRUN", "+", {})
        datafile = absolute_filename('data.txt')
        script = """
            fname : std.Constant(data="%s")
            src   : io.FileReader()
            join  : text.LineJoin()
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            fname.token > src.filename
            src.out   > join.line
            join.text > snk.token
        """ % (datafile, )
        app_info, errors, warnings = self.compile_script(script, "testBasicJoin")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)

        snk = d.actor_map['testBasicJoin:snk']
        actual = request_handler.report(self.rt1, snk)
        with open(datafile, "r") as fp:
            expected = ["\n".join([l.rstrip() for l in fp.readlines()])]

        self.assert_lists_equal(expected, actual, min_length=1)

        d.destroy()

    @pytest.mark.xfail
    def testCustomTriggerJoin(self):
        _log.analyze("TESTRUN", "+", {})
        datafile = absolute_filename('data.txt')
        script = """
            fname : std.Constant(data="%s")
            src   : io.FileReader()
            join  : text.LineJoin()
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            fname.token > src.filename
            src.out   > join.line
            join.text > snk.token
        """ % (datafile, )
        app_info, errors, warnings = self.compile_script(script, "testCustomTriggerJoin")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testCustomTriggerJoin:snk']
        actual = request_handler.report(self.rt1, snk)
        with open(datafile, "r") as fp:
            expected = [l.rstrip() for l in fp.readlines()]
            expected = ['\n'.join(expected[:4]), '\n'.join(expected[4:])]

        self.assert_lists_equal(expected, actual, min_length=2)

        d.destroy()

    @pytest.mark.xfail
    def testEmptyStringTriggerJoin(self):
        _log.analyze("TESTRUN", "+", {})
        datafile = absolute_filename('data.txt')
        script = """
            fname : std.Constant(data="%s")
            src   : io.FileReader()
            join  : text.LineJoin()
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            fname.token > src.filename
            src.out   > join.line
            join.text > snk.token
        """ % (datafile, )
        app_info, errors, warnings = self.compile_script(script, "testCustomTriggerJoin")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testCustomTriggerJoin:snk']
        actual = request_handler.report(self.rt1, snk)
        with open(datafile, "r") as fp:
            expected = [l.rstrip() for l in fp.readlines()]
            expected = ['\n'.join(expected[:10]), '\n'.join(expected[10:])]

        self.assert_lists_equal(expected, actual, min_length=2)

        d.destroy()



@pytest.mark.essential
class TestRegex(CalvinTestBase):

    def testRegexMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexMatch:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["24.1632"]

        self.assert_lists_equal(expected, actual, min_length=1)

        d.destroy()


    def testRegexNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632", n=1)
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexNoMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexNoMatch:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["x24.1632"]

        self.assert_lists_equal(expected, actual, min_length=1)

        d.destroy()

    def testRegexCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCapture")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexCapture:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["24"]

        self.assert_lists_equal(expected, actual, min_length=1)

        d.destroy()

    def testRegexMultiCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.(\d+)")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMultiCapture")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexMultiCapture:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["24"]

        self.assert_lists_equal(expected, actual, min_length=1)

        d.destroy()


    def testRegexCaptureNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCaptureNoMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexCaptureNoMatch:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["x24.1632"]

        self.assert_lists_equal(expected, actual, min_length=1)

        d.destroy()

@pytest.mark.essential
class TestConstantAsArguments(CalvinTestBase):

    def testConstant(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = 42
            src   : std.Constant(data=FOO, n=10)
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstant")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstant:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [42]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testConstantRecursive(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = 42
            src   : std.Constant(data=FOO, n=10)
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursive")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstantRecursive:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [42]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()


@pytest.mark.essential
class TestConstantOnPort(CalvinTestBase):

    def testLiteralOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            42 > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testLiteralOnPort:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = [42]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testConstantOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = "Hello"
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstantOnPort:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["Hello"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testConstantRecursiveOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = "yay"
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursiveOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstantRecursiveOnPort:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["yay"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()


@pytest.mark.essential
class TestConstantAndComponents(CalvinTestBase):

    def testLiteralOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Foo() -> out {
                i:std.Stringify()
                42 > i.in
                i.out > .out
            }
            src   : Foo()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnCompPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testLiteralOnCompPort:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["42"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testConstantOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define MEANING = 42
            component Foo() -> out {
                i:std.Stringify()
                MEANING > i.in
                i.out > .out
            }
            src   : Foo()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnCompPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstantOnCompPort:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["42"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testStringConstantOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define MEANING = "42"
            component Foo() -> out {
                i:std.Identity()
                MEANING > i.token
                i.token > .out
            }
            src   : Foo()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testStringConstantOnCompPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testStringConstantOnCompPort:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["42"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

@pytest.mark.essential
class TestConstantAndComponentsArguments(CalvinTestBase):

    def testComponentArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(len) -> seq {
            src : std.Constant(data="hup", n=len)
            src.token > .seq
        }
        src : Count(len=5)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgument")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testComponentArgument:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["hup"]*5

        self.assert_lists_equal(expected, actual, min_length=5)

        d.destroy()

    def testComponentConstantArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 5
        component Count(len) -> seq {
            src : std.Constant(data="hup", n=len)
            src.token > .seq
        }
        src : Count(len=FOO)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgument")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testComponentConstantArgument:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["hup"]*5

        self.assert_lists_equal(expected, actual, min_length=5)

        d.destroy()



    def testComponentConstantArgumentDirect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 10
        component Count() -> seq {
         src : std.Constant(data="hup", n=FOO)
         src.token > .seq
        }
        src : Count()
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentDirect")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testComponentConstantArgumentDirect:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["hup"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()


    def testComponentArgumentAsImplicitActor(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(data) -> seq {
            i : std.Identity()
            data > i.token
            i.token > .seq
        }
        src : Count(data="hup")
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgumentAsImplicitActor")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testComponentArgumentAsImplicitActor:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["hup"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()


    def testComponentConstantArgumentAsImplicitActor(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = "hup"
        component Count(data) -> seq {
            i : std.Identity()
            data > i.token
            i.token > .seq
        }
        src : Count(data=FOO)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentAsImplicitActor")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testComponentConstantArgumentAsImplicitActor:snk']
        actual = request_handler.report(self.rt1, snk)
        expected = ["hup"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()
