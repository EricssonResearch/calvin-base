# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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
import pytest
import numbers

from calvin.utilities import calvinconfig
from calvin.csparser import cscompile as compiler
from calvin.Tools import cscompiler as compile_tool
from calvin.Tools import deployer
from calvin.utilities import calvinlogger
from calvin.requests.request_handler import RequestHandler
from . import helpers

_log = calvinlogger.get_logger(__name__)


def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


runtime = None
test_type = None
request_handler = None


def deploy_app(deployer, runtimes=None):
    runtimes = runtimes if runtimes else [ deployer.runtime ]
    return helpers.deploy_app(request_handler, deployer, runtimes)

def expected_tokens(rt, actor_id, t_type='seq'):
    return helpers.expected_tokens(request_handler, rt, actor_id, t_type)

def wait_for_tokens(rt, actor_id, size=5, retries=20):
    return helpers.wait_for_tokens(request_handler, rt, actor_id, size, retries)

def actual_tokens(rt, actor_id, size=5, retries=20):
    return helpers.actual_tokens(request_handler, rt, actor_id, size, retries)

def actual_tokens_multiple(rt, actor_ids, size=5, retries=20):
    return helpers.actual_tokens_multiple(request_handler, rt, actor_ids, size, retries)

def assert_lists_equal(expected, actual, min_length=5):
    assert len(actual) >= min_length
    assert actual
    assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True)

def wait_until_nbr(rt, actor_id, size=5, retries=20, sleep=0.1):
    for i in range(retries):
        r = request_handler.report(rt, actor_id)
        l = r if isinstance(r, numbers.Number) else len(r)
        if l >= size:
            break
        time.sleep(sleep)
    assert l >= size

def setup_module(module):
    global runtime
    global request_handler
    global test_type

    request_handler = RequestHandler()
    test_type, [runtime] = helpers.setup_test_type(request_handler, nbr=1)


def teardown_module(module):
    global runtime
    global test_type
    global request_handler

    helpers.teardown_test_type(test_type, [runtime], request_handler)


class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.runtime = runtime


    def assert_lists_equal(self, expected, actual, min_length=5):
        self.assertTrue(len(actual) >= min_length, "Received data too short (%d), need at least %d" % (len(actual), min_length))
        self._assert_lists_equal(expected, actual)

    def _assert_lists_equal(self, expected, actual):
        assert actual
        assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True)

    def get_port_property(self, app_info, actor, port, direction, key):
        """Access port properties in a robust way since order might change between parser revisions"""
        # Get list of port properties
        props = app_info['port_properties'][actor]
        for p in props:
            found = p['direction'] == direction and p['port'] == port
            if not found:
                continue
            return p['properties'][key]
        raise KeyError("Property '{}' not present.".format(key))

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
        #import sys
        #from twisted.python import log
        #from twisted.internet import defer
        #log.startLogging(sys.stdout)
        #defer.setDebugging(True)

        assert request_handler.get_node(self.runtime, self.runtime.id)['uris'] == self.runtime.uris

@pytest.mark.essential
@pytest.mark.slow
class TestLocalConnectDisconnect(CalvinTestBase):

    """Testing local connect/disconnect/re-connect"""

    def testLocalSourceSink(self):
        """Testing local source and sink"""

        rt = self.runtime

        # Setup
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')

        # Wait for some tokens to arrive
        wait_for_tokens(rt, snk)

        # Check what was sent
        expected = expected_tokens(rt, src, 'seq')
        # Wait for it to arrive
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        # Assert the sent and arrived are identical
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectSink(self):
        """Testing local connect/disconnect/re-connect on sink"""

        rt = self.runtime

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "test.Sink", "snk", store_tokens=1, quiet=1)

        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')

        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)

        # Disconnect/reconnect
        request_handler.disconnect(rt, snk)
        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')

        # Wait for at least one more token
        wait_for_tokens(rt, snk, len(actual)+1)

        # Fetch what was sent/received
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, snk)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectSource(self):
        """Testing local connect/disconnect/re-connect on source"""

        rt = self.runtime

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "test.Sink", "snk", store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, "token", rt.id, src, "integer")

        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)

        # disconnect/reconnect
        request_handler.disconnect(rt, src)
        request_handler.connect(rt, snk, "token", rt.id, src, "integer")

        # Wait for one more token
        wait_for_tokens(rt, snk, len(actual)+1)

        # Fetch what was sent/received
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectFilter(self):
        """Testing local connect/disconnect/re-connect on filter"""

        rt = self.runtime

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        csum = request_handler.new_actor(rt, "std.Sum", "sum")
        snk = request_handler.new_actor_wargs(rt, "test.Sink", "snk", store_tokens=1, quiet=1)

        request_handler.connect(rt, snk, "token", rt.id, csum, "integer")
        request_handler.connect(rt, csum, "integer", rt.id, src, "integer")

        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)

        # disconnect/reconnect
        request_handler.disconnect(rt, csum)
        request_handler.connect(rt, snk, "token", rt.id, csum, "integer")
        request_handler.connect(rt, csum, "integer", rt.id, src, "integer")

        # Wait for one more token
        wait_for_tokens(rt, snk, len(actual)+1)

        # Fetch sent/received
        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, csum)
        request_handler.delete_actor(rt, snk)

    def testTimerLocalSourceSink(self):
        """Testing timer based local source and sink"""

        rt = self.runtime

        src = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src', sleep=0.1, steps=10)
        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')

        # Wait for some tokens
        wait_for_tokens(rt, snk)

        # Check what was sent/received
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)


@pytest.mark.essential
@pytest.mark.slow
class TestCalvinScript(CalvinTestBase):

    def testCompileSimple(self):
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token
    """

        rt = self.runtime
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        deploy_app(d)

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        wait_for_tokens(rt, snk)
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))
        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testDestroyAppWithLocalActors(self):
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token
    """

        rt = self.runtime
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)

        deploy_app(d)
        app_id = d.app_id

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        applications = request_handler.get_applications(rt)
        assert app_id in applications

        helpers.destroy_app(d)

        applications = request_handler.get_applications(rt)
        assert app_id not in applications

        actors = request_handler.get_actors(rt)
        assert src not in actors
        assert snk not in actors


@pytest.mark.essential
class TestConnections(CalvinTestBase):

    @pytest.mark.slow
    def testLocalSourceSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.runtime, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.runtime, snk, 'token', self.runtime.id, src, 'integer')

        actual = wait_for_tokens(self.runtime, snk)
        expected = expected_tokens(self.runtime, src, 'seq')

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(self.runtime, src)
        request_handler.delete_actor(self.runtime, snk)


@pytest.mark.essential
class TestScripts(CalvinTestBase):

    @pytest.mark.slow
    def testInlineScript(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : test.Sink(store_tokens=1, quiet=1)
          src.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['simple:snk']
        src = d.actor_map['simple:src']

        actual = wait_for_tokens(self.runtime, snk)
        expected = expected_tokens(self.runtime, src)

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

    @pytest.mark.slow
    def testFileScript(self):
        _log.analyze("TESTRUN", "+", {})
        scriptname = 'test1'
        scriptfile = absolute_filename("scripts/%s.calvin" % (scriptname, ))
        app_info, issuetracker = compile_tool.compile_file(scriptfile, ds=False, ir=False)
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        src = d.actor_map['%s:src' % scriptname]
        snk = d.actor_map['%s:snk' % scriptname]

        actual = wait_for_tokens(self.runtime, snk)
        expected = expected_tokens(self.runtime, src)

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestEnabledToEnabledBug(CalvinTestBase):

    def test10(self):
        _log.analyze("TESTRUN", "+", {})
        # Two actors, doesn't seem to trigger the bug
        src = request_handler.new_actor(self.runtime, 'std.Counter', 'src')
        snk = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.runtime, snk, 'token', self.runtime.id, src, 'integer')

        actual = actual_tokens(self.runtime, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.runtime, src)
        request_handler.delete_actor(self.runtime, snk)

    def test11(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test10, but scripted
        script = """
            src : std.Counter()
            snk : test.Sink(store_tokens=1, quiet=1)

            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['simple:snk']

        actual = actual_tokens(self.runtime, snk, 10)
        self.assert_lists_equal(range(1, 10), actual)

        helpers.destroy_app(d)

    def test20(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.runtime, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.runtime, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.runtime, snk, 'token', self.runtime.id, ity, 'token')
        request_handler.connect(self.runtime, ity, 'token', self.runtime.id, src, 'integer')

        actual = actual_tokens(self.runtime, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.runtime, src)
        request_handler.delete_actor(self.runtime, ity)
        request_handler.delete_actor(self.runtime, snk)

    def test25(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.runtime, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.runtime, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.runtime, ity, 'token', self.runtime.id, src, 'integer')
        request_handler.connect(self.runtime, snk, 'token', self.runtime.id, ity, 'token')

        actual = actual_tokens(self.runtime, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.runtime, src)
        request_handler.delete_actor(self.runtime, ity)
        request_handler.delete_actor(self.runtime, snk)

    def test26(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test20
        script = """
            src : std.Counter()
            ity : std.Identity()
            snk : test.Sink(store_tokens=1, quiet=1)

            src.integer > ity.token
            ity.token > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)
        snk = d.actor_map['simple:snk']

        actual = actual_tokens(self.runtime, snk, 10)
        self.assert_lists_equal(range(1,10), actual)

        helpers.destroy_app(d)


    def test30(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.runtime, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(self.runtime, src, 'out', 'integer',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(self.runtime, snk1, 'token', self.runtime.id, src, 'integer')
        request_handler.connect(self.runtime, snk2, 'token', self.runtime.id, src, 'integer')

        actual1 = actual_tokens(self.runtime, snk1, 10)
        actual2 = actual_tokens(self.runtime, snk2, 10)

        self.assert_lists_equal(list(range(1, 10)), actual1)
        self.assert_lists_equal(list(range(1, 10)), actual2)

        request_handler.delete_actor(self.runtime, src)
        request_handler.delete_actor(self.runtime, snk1)
        request_handler.delete_actor(self.runtime, snk2)

    def test31(self):
        # Verify that fanout defined implicitly in scripts is handled correctly
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)

            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test31")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk1 = d.actor_map['test31:snk1']
        snk2 = d.actor_map['test31:snk2']
        actual1 = actual_tokens(self.runtime, snk1, 10)
        actual2 = actual_tokens(self.runtime, snk2, 10)
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

            snk2 : test.Sink(store_tokens=1, quiet=1)
            snk1 : test.Sink(store_tokens=1, quiet=1)
            foo : Foo()
            req : std.Counter()
            req.integer > foo.in
            foo.a > snk1.token
            foo.b > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test32")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk1 = d.actor_map['test32:snk1']
        snk2 = d.actor_map['test32:snk2']
        actual1 = actual_tokens(self.runtime, snk1, 10)
        actual2 = actual_tokens(self.runtime, snk2, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)

        d.destroy()

    def test40(self):
        # Verify round robin port
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.runtime, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(self.runtime, 'test.Sink', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(self.runtime, src, 'out', 'integer',
                                            port_properties={'routing': 'round-robin', 'nbr_peers': 2})

        request_handler.connect(self.runtime, snk1, 'token', self.runtime.id, src, 'integer')
        request_handler.connect(self.runtime, snk2, 'token', self.runtime.id, src, 'integer')

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = actual_tokens(self.runtime, snk1, 10)
        actual2 = actual_tokens(self.runtime, snk2, 10)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        request_handler.delete_actor(self.runtime, src)
        request_handler.delete_actor(self.runtime, snk1)
        request_handler.delete_actor(self.runtime, snk2)




@pytest.mark.essential
class TestNullPorts(CalvinTestBase):

    def testVoidActor(self):
        # Verify that the null port of a flow.Void actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src1 : std.Counter()
            src2 : flow.Void()
            join : flow.Join()
            snk  : test.Sink(store_tokens=1, quiet=1)

            src1.integer > join.token_1
            src2.void > join.token_2
            join.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testVoidActor")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testVoidActor:snk']
        actual = wait_for_tokens(self.runtime, snk, 10)
        expected = list(range(1, 10))
        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

    def testTerminatorActor(self):
        # Verify that the null port of a flow.Terminator actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src  : std.Counter()
            term : flow.Terminator()
            snk  : test.Sink(store_tokens=1, quiet=1)

            src.integer > term.void
            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testTerminatorActor")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testTerminatorActor:snk']
        actual = wait_for_tokens(self.runtime, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


@pytest.mark.essential
class TestCompare(CalvinTestBase):

    def testBadOp(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5)
            pred  : std.Compare(rel="<>")
            snk   : test.Sink(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadOp")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testBadOp:snk']
        actual = wait_for_tokens(self.runtime, snk, 10)
        expected = [0] * 10

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5)
            pred  : std.Compare(rel="=")
            snk   : test.Sink(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testEqual")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testEqual:snk']

        expected = [x == 5 for x in range(1, 10)]
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


    def testGreaterThanOrEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5)
            pred  : std.Compare(rel=">=")
            snk   : test.Sink(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testGreaterThanOrEqual")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testGreaterThanOrEqual:snk']
        expected = [x >= 5 for x in range(1, 10)]
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)



@pytest.mark.essential
class TestSelect(CalvinTestBase):

    def testTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=true)
            route : flow.Select()
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > snk.token
            route.case_false > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testTrue")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testTrue:snk']
        actual = wait_for_tokens(self.runtime, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=0)
            route : flow.Select()
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testFalse")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testFalse:snk']

        actual = wait_for_tokens(self.runtime, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


    def testBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=2)
            route : flow.Select()
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadSelect")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testBadSelect:snk']
        actual = wait_for_tokens(self.runtime, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestDeselect(CalvinTestBase):

    def testDeselectTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0)
            const_1 : std.Constant(data=1)
            comp    : std.Compare(rel="<=")
            ds      : flow.Deselect()
            snk     : test.Sink(store_tokens=1, quiet=1)

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
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testDeselectTrue:snk']

        expected = [1] * 5 + [0] * 5
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)
        helpers.destroy_app(d)

    def testDeselectFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0)
            const_1 : std.Constant(data=1)
            comp    : std.Compare(rel="<=")
            ds      : flow.Deselect()
            snk     : test.Sink(store_tokens=1, quiet=1)

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
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testDeselectFalse:snk']

        expected = [0] * 5 + [1] * 5
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


    def testDeselectBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0)
            ds      : flow.Deselect()
            snk     : test.Sink(store_tokens=1, quiet=1)

            const_0.token > ds.case_false
            src.integer > ds.case_true
            const_0.token > const_5.in
            const_5.out > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectBadSelect")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testDeselectBadSelect:snk']

        expected = [0] * 10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestLineJoin(CalvinTestBase):

    def testBasicJoin(self):
        _log.analyze("TESTRUN", "+", {})
        datafile = absolute_filename('data.txt')
        script = """
            fname : std.Constant(data="%s")
            src   : io.FileReader()
            join  : text.LineJoin()
            snk   : test.Sink(store_tokens=1, quiet=1)

            fname.token > src.filename
            src.out   > join.line
            join.text > snk.token
        """ % (datafile, )

        app_info, errors, warnings = self.compile_script(script, "testBasicJoin")
        print errors

        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        with open(datafile, "r") as fp:
            expected = ["\n".join([l.rstrip() for l in fp.readlines()])]

        snk = d.actor_map['testBasicJoin:snk']

        actual = wait_for_tokens(self.runtime, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestRegex(CalvinTestBase):

    def testRegexMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632")
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMatch")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexMatch:snk']

        expected = ["24.1632"]
        actual = wait_for_tokens(self.runtime, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)



    def testRegexNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632")
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexNoMatch")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexNoMatch:snk']
        expected = ["x24.1632"]
        actual = wait_for_tokens(self.runtime, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632")
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCapture")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexCapture:snk']

        expected = ["24"]
        actual = wait_for_tokens(self.runtime, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexMultiCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632")
            regex : text.RegexMatch(regex=!"(\d+)\.(\d+)")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMultiCapture")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexMultiCapture:snk']

        expected = ["24"]
        actual = wait_for_tokens(self.runtime, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexCaptureNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632")
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCaptureNoMatch")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexCaptureNoMatch:snk']
        expected = ["x24.1632"]
        actual = wait_for_tokens(self.runtime, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestConstantAsArguments(CalvinTestBase):

    def testConstant(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = 42
            src   : std.Constant(data=FOO)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstant")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstant:snk']

        expected = [42]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantRecursive(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = 42
            src   : std.Constant(data=FOO)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursive")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantRecursive:snk']

        expected = [42]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestConstantOnPort(CalvinTestBase):

    def testLiteralOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            snk   : test.Sink(store_tokens=1, quiet=1)
            42 > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPort")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)
        time.sleep(.1)

        snk = d.actor_map['testLiteralOnPort:snk']

        expected = [42]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = "Hello"
            snk   : test.Sink(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnPort")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantOnPort:snk']

        expected = ["Hello"]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantRecursiveOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = "yay"
            snk   : test.Sink(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursiveOnPort")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantRecursiveOnPort:snk']

        expected = ["yay"]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


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
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnCompPort")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testLiteralOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

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
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnCompPort")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

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
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testStringConstantOnCompPort")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testStringConstantOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestConstantAndComponentsArguments(CalvinTestBase):

    def testComponentArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(len) -> seq {
            src : test.FiniteCounter(start=1, steps=len)
            src.integer > .seq
        }
        src : Count(len=5)
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgument")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentArgument:snk']

        expected = [1,2,3,4,5]
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=5)

        helpers.destroy_app(d)

    def testComponentConstantArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 5
        component Count(len) -> seq {
            src : test.FiniteCounter(start=1, steps=len)
            src.integer > .seq
        }
        src : Count(len=FOO)
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgument")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgument:snk']

        expected = [1,2,3,4,5]
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=5)

        helpers.destroy_app(d)


    def testComponentConstantArgumentDirect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 10
        component Count() -> seq {
         src : test.FiniteCounter(start=1, steps=FOO)
         src.integer > .seq
        }
        src : Count()
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentDirect")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgumentDirect:snk']

        expected = [1,2,3,4,5,6,7,8,9,10]
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testComponentArgumentAsImplicitActor(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(data) -> seq {
            i : std.Identity()
            data > i.token
            i.token > .seq
        }
        src : Count(data="hup")
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgumentAsImplicitActor")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentArgumentAsImplicitActor:snk']

        expected = ["hup"]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

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
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentAsImplicitActor")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgumentAsImplicitActor:snk']

        expected = ["hup"]*10
        actual = wait_for_tokens(self.runtime, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)
        d.destroy()

@pytest.mark.essential
class TestConstantifyOnPort(CalvinTestBase):

    def testLiteralOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk : test.Sink(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPort")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testLiteralOnPort:snk']

        actual = wait_for_tokens(self.runtime, snk, 10)
        expected = ['X']*len(actual)

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testLiteralOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk1.token, snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPortlist")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk1 = d.actor_map['testLiteralOnPortlist:snk1']
        snk2 = d.actor_map['testLiteralOnPortlist:snk2']

        actual1 = wait_for_tokens(self.runtime, snk1, 10)
        actual2 = wait_for_tokens(self.runtime, snk2, 10)

        expected1 = ['X']*len(actual1)
        expected2 = range(1, len(actual2))

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testLiteralsOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk1.token, /"Y"/ snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralsOnPortlist")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk1 = d.actor_map['testLiteralsOnPortlist:snk1']
        snk2 = d.actor_map['testLiteralsOnPortlist:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 10)
        actual2 = wait_for_tokens(self.runtime, snk2, 10)

        expected1 = ['X']*len(actual1)
        expected2 = ['Y']*len(actual2)

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testConstantsOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = "X"
            define BAR = "Y"
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)
            src.integer > /FOO/ snk1.token, /BAR/ snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantsOnPortlist")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk1 = d.actor_map['testConstantsOnPortlist:snk1']
        snk2 = d.actor_map['testConstantsOnPortlist:snk2']

        actual1 = wait_for_tokens(self.runtime, snk1, 10)
        actual2 = wait_for_tokens(self.runtime, snk2, 10)
        expected1 = ['X']*len(actual1)
        expected2 = ['Y']*len(actual2)

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testLiteralOnComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Ticker() trigger -> out {
                id : std.Identity()
                .trigger > /"X"/ id.token
                id.token > .out
            }

            tick : std.Trigger(data="tick", tick=0.1)
            ticker : Ticker()
            test : test.Sink(store_tokens=1, quiet=1)

            tick.data > ticker.trigger
            ticker.out > test.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnComponentInPort")
        d = deployer.Deployer(self.runtime, app_info)
        deploy_app(d)

        snk = d.actor_map['testLiteralOnComponentInPort:test']

        actual = wait_for_tokens(self.runtime, snk, 10)
        expected = ['X']*len(actual)

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()


@pytest.mark.essential
class TestPortProperties(CalvinTestBase):

    def testRoundRobin(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyOutsideComponentOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq(routing="round-robin")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self. get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyOutsideComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing="round-robin")
            snk1.seq(test1="dummy1")
            snk2.seq(test1="dummy2")
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk1:compsnk', 'token', 'in', 'test1') == 'dummy1')
        assert 'port' in app_info['port_properties']['testScript:snk2:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk2:compsnk', 'token', 'in', 'test1') == 'dummy2')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing="round-robin")
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
                compsnk.token(test1="dummyx")
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing="round-robin")
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk1:compsnk', 'token', 'in', 'test1') == 'dummyx')
        assert 'port' in app_info['port_properties']['testScript:snk2:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk2:compsnk', 'token', 'in', 'test1') == 'dummyx')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentInternalInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                .seq(test1="dummyx")
                compsrc.integer(routing="round-robin")
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1'][0]
        assert (app_info['port_properties']['testScript:snk1'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1') == 'dummyx')
        assert 'port' in app_info['port_properties']['testScript:snk2'][0]
        assert (app_info['port_properties']['testScript:snk2'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test1') == 'dummyx')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentInternalOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
                .seq(routing="round-robin")
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing') == 'round-robin')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyTupleOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')[0] == 'round-robin')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')[1] == 'random')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyConsolidateOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq(routing=["dummy", "round-robin"])
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert len(errors) == 0
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert len(self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')) == 1
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')[0] == 'round-robin')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    @pytest.mark.xfail(reason="Line numbers are not properly propagated for error reporting")
    def testPortPropertyConsolidateRejectOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq(routing="fanout")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert len(errors) == 2
        assert all([e['reason'] == "Can't handle conflicting properties without common alternatives" for e in errors])
        assert all([e['line'] in [5, 11] for e in errors])

    def testPortPropertyConsolidateInsideComponentInternalOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
                .seq(routing=["random", "round-robin", "fanout"])
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing=["round-robin", "random"])
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert len(self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing')) == 2
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing')[0] == 'round-robin')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyConsolidateInsideComponentInternalInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                .seq(test1=["dummyx", "dummyy", "dummyz"], test2="dummyi")
                compsrc.integer(routing="round-robin")
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            snk1.token(test1=["dummyz", "dummyy"])
            snk2.token(test1="dummyy")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1'][0]
        assert (app_info['port_properties']['testScript:snk1'][0]['port'] ==
                'token')
        assert len(self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1')) == 2
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1')[0] == 'dummyz')
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1')[1] == 'dummyy')
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test2') == 'dummyi')
        assert 'port' in app_info['port_properties']['testScript:snk2'][0]
        assert (app_info['port_properties']['testScript:snk2'][0]['port'] ==
                'token')
        assert len(self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test1')) == 1
        assert (self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test1')[0] == 'dummyy')
        assert (self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test2') == 'dummyi')

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(self.runtime, snk1, 11)
        actual2 = wait_for_tokens(self.runtime, snk2, 11)

        snk1_meta = request_handler.get_actor(self.runtime, snk1)
        snk2_meta = request_handler.get_actor(self.runtime, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

@pytest.mark.essential
class TestCollectPort(CalvinTestBase):

    def testCollectPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert 'testCollectPort:snk' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testCollectPort:snk'][0]
        assert (app_info['port_properties']['testCollectPort:snk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testCollectPort:snk', 'token', 'in', 'nbr_peers') == 2)

        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk = d.actor_map['testCollectPort:snk']
        actual = wait_for_tokens(self.runtime, snk, 10)

        high = [x for x in actual if x > 999]
        low = [x for x in actual if x < 999]
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        helpers.destroy_app(d)

    def testCollectPortComponentIn(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Dual() seqin -> seqout1, seqout2 {
            id1    : std.Identity()
            id2    : std.Identity()
            .seqin(routing="round-robin")
            .seqin > id1.token
            .seqin > id2.token
            id1.token > .seqout1
            id2.token > .seqout2
        }
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        duo: Dual()
        duo.seqin(routing="collect-unordered")
        snk1 : test.Sink(store_tokens=1, quiet=1)
        snk2 : test.Sink(store_tokens=1, quiet=1)
        src1.integer > duo.seqin
        src2.integer > duo.seqin
        duo.seqout1 > snk1.token
        duo.seqout2 > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:duo:id1'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:duo:id2'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testCollectPort:duo:id1', 'token', 'in', 'nbr_peers') == 2)
        assert (self.get_port_property(app_info, 'testCollectPort:duo:id2', 'token', 'in', 'nbr_peers') == 2)
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testCollectPort:snk1']
        snk2 = d.actor_map['testCollectPort:snk2']
        actual1, actual2 = actual_tokens_multiple(self.runtime, [snk1, snk2], 10)

        high = sorted([x for x in actual1 + actual2 if x > 999])
        low = sorted([x for x in actual1 + actual2 if x < 999])
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        helpers.destroy_app(d)

    def testCollectPortComponentOut(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Dual() seqin1, seqin2 -> seqout {
            id1    : std.Identity()
            id2    : std.Identity()
            .seqout(routing="collect-unordered")
            .seqin1 > id1.token
            .seqin2 > id2.token
            id1.token > .seqout
            id2.token > .seqout
        }
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        duo: Dual()
        duo.seqout(routing="round-robin")
        snk1 : test.Sink(store_tokens=1, quiet=1)
        snk2 : test.Sink(store_tokens=1, quiet=1)
        src1.integer > duo.seqin1
        src2.integer > duo.seqin2
        duo.seqout > snk1.token
        duo.seqout > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:snk1'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:snk2'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testCollectPort:snk1', 'token', 'in', 'nbr_peers') == 2)
        assert (self.get_port_property(app_info, 'testCollectPort:snk2', 'token', 'in', 'nbr_peers') == 2)
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()

        snk1 = d.actor_map['testCollectPort:snk1']
        snk2 = d.actor_map['testCollectPort:snk2']
        actual1, actual2 = actual_tokens_multiple(self.runtime, [snk1, snk2], 10)

        high = sorted([x for x in actual1 + actual2 if x > 999])
        low = sorted([x for x in actual1 + actual2 if x < 999])
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        helpers.destroy_app(d)

@pytest.mark.essential
class TestPortRouting(CalvinTestBase):

    def testCollectOneTagPortWithException(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : test.FiniteCounter(start=1, steps=3, repeat=true)
        src2 : test.FiniteCounter(start=1001, steps=100)
        expt : exception.ExceptionHandler(replace=true, replacement="exception")
        snk : test.Sink(store_tokens=1, quiet=1)
        exptsnk : test.Sink(store_tokens=1, quiet=1)
        expt.token[in](routing="collect-tagged")
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > expt.token
        src2.integer > expt.token
        expt.token > snk.token
        expt.status > exptsnk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        exptsnk = d.actor_map['testCollectPort:exptsnk']
        exceptions = wait_for_tokens(self.runtime, exptsnk, 10)
        actual = request_handler.report(self.runtime, snk)
        assert len(actual) >= 3 * 10
        print actual, exceptions

        self.assert_lists_equal(exceptions, [{u'src_one': u'End of stream'}]*10)
        high = [x['src_two'] for x in actual if isinstance(x, dict) and 'src_two' in x]
        low = [x['src_one'] for x in actual if isinstance(x, dict) and 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high, min_length=15)
        self.assert_lists_equal(range(1,4)*10, low, min_length=15)

        helpers.destroy_app(d)

    def testCollectAnyTagPortWithException(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : test.FiniteCounter(start=1, steps=3, repeat=true)
        src2 : test.FiniteCounter(start=1001, steps=100)
        expt : exception.ExceptionHandler(replace=true, replacement="exception")
        snk : test.Sink(store_tokens=1, quiet=1)
        exptsnk : test.Sink(store_tokens=1, quiet=1)
        expt.token[in](routing="collect-any-tagged")
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > expt.token
        src2.integer > expt.token
        expt.token > snk.token
        expt.status > exptsnk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        exptsnk = d.actor_map['testCollectPort:exptsnk']
        exceptions = wait_for_tokens(self.runtime, exptsnk, 10)
        actual = request_handler.report(self.runtime, snk)
        assert len(actual) >= 3 * 10
        print actual, exceptions

        self.assert_lists_equal(exceptions, [{u'src_one': u'End of stream'}]*10)
        high = [x['src_two'] for x in actual if isinstance(x, dict) and 'src_two' in x]
        low = [x['src_one'] for x in actual if isinstance(x, dict) and 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high, min_length=15)
        self.assert_lists_equal(range(1,4)*10, low, min_length=15)

        helpers.destroy_app(d)

    def testCollectAllTagPortWithException(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : test.FiniteCounter(start=1, steps=3, repeat=true)
        src2 : test.FiniteCounter(start=1001, steps=100)
        expt : exception.ExceptionHandler(replace=true, replacement="exception")
        snk : test.Sink(store_tokens=1, quiet=1)
        exptsnk : test.Sink(store_tokens=1, quiet=1)
        expt.token[in](routing="collect-all-tagged")
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > expt.token
        src2.integer > expt.token
        expt.token > snk.token
        expt.status > exptsnk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.runtime, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        exptsnk = d.actor_map['testCollectPort:exptsnk']
        exceptions = wait_for_tokens(self.runtime, exptsnk, 10)
        actual = request_handler.report(self.runtime, snk)
        assert len(actual) >= 3 * 10
        print actual, exceptions

        self.assert_lists_equal(exceptions, [{u'src_one': u'End of stream'}]*10)
        high = [x['src_two'] for x in actual if isinstance(x, dict) and 'src_two' in x]
        low = [x['src_one'] for x in actual if isinstance(x, dict) and 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high, min_length=15)
        self.assert_lists_equal(range(1,4)*10, low, min_length=15)

        # Test that kept in sync but skewed one token for every exception
        comp = [x['src_two'] - x['src_one'] - 1000 for x in actual if isinstance(x, dict)]
        self.assert_lists_equal(range(0,45,3), comp[0::3], min_length=5)
        self.assert_lists_equal(range(0,45,3), comp[1::3], min_length=5)
        self.assert_lists_equal(range(0,45,3), comp[2::3], min_length=5)
        helpers.destroy_app(d)

@pytest.mark.essential
@pytest.mark.slow
class TestDeployScript(CalvinTestBase):

    def testDeployScriptSimple(self):
        script = r"""
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token

      rule simple: node_attr_match(index=["node_name", {"organization": "com.ericsson"}])
      apply src, snk: simple
        """

        rt = self.runtime
        response = helpers.deploy_script(request_handler, "simple", script, rt)

        print response

        src = response['actor_map']['simple:src']
        snk = response['actor_map']['simple:snk']

        rt_src = request_handler.get_node(rt, response['placement'][src][0])["control_uris"]
        rt_snk = request_handler.get_node(rt, response['placement'][snk][0])["control_uris"]

        assert response["requirements_fulfilled"]

        wait_for_tokens(rt_src[0], snk)
        expected = expected_tokens(rt_src[0], src, 'seq')
        actual = actual_tokens(rt_snk[0], snk, len(expected))
        request_handler.disconnect(rt_src[0], src)

        self.assert_lists_equal(expected, actual)
        helpers.delete_app(request_handler, rt, response['application_id'])

class TestPortmappingScript(CalvinTestBase):

    def _run_test(self, script, minlen):
        rt = self.runtime
        response = helpers.deploy_script(request_handler, "simple", script, rt)
        snk = response['actor_map']['simple:snk']
        wait_for_tokens(rt, snk, minlen)
        actual = actual_tokens(rt, snk)
        helpers.delete_app(request_handler, rt, response['application_id'])
        return actual

    def testSimple(self):
        script = r"""
        dummy : std.Constantify(constant=42)
        cdict : flow.CollectCompleteDict(mapping={"dummy":&dummy.out})
        snk : test.Sink(store_tokens=1, quiet=1)

        1 > dummy.in
        dummy.out > cdict.token
        cdict.dict > snk.token
        """

        expected = [{u'dummy': 42}]*5
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)

    def testMapAlternate(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        input: std.Counter()
        alt: flow.Alternate(order=[&out1.out, &out2.out, &out3.out])
        out1 : text.PrefixString(prefix="tag-1:")
        out2 : text.PrefixString(prefix="tag-2:")
        out3 : text.PrefixString(prefix="tag-3:")
        input.integer > out1.in
        input.integer > out2.in
        input.integer > out3.in
        out1.out > alt.token
        out2.out > alt.token
        out3.out > alt.token
        alt.token > snk.token
        """
        expected = [
            "tag-1:1",
            "tag-2:1",
            "tag-3:1",
            "tag-1:2",
            "tag-2:2",
            "tag-3:2",
            "tag-1:3",
            "tag-2:3",
            "tag-3:3",
            "tag-1:4",
            "tag-2:4",
            "tag-3:4"
        ]
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)

    def testMapDealternate(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        input: std.Counter()
        switch: flow.Dealternate(order=[&out3.in, &out1.in, &out2.in])
        out1 : text.PrefixString(prefix="tag-1:")
        out2 : text.PrefixString(prefix="tag-2:")
        out3 : text.PrefixString(prefix="tag-3:")
        collect : flow.Alternate(order=[&out1.out, &out2.out, &out3.out])
        input.integer > switch.token
        switch.token > out1.in
        switch.token > out2.in
        switch.token > out3.in
        out1.out > collect.token
        out2.out > collect.token
        out3.out > collect.token
        collect.token > snk.token
        """
        expected = [
            "tag-1:2",
            "tag-2:3",
            "tag-3:1",
            "tag-1:5",
            "tag-2:6",
            "tag-3:4",
            "tag-1:8",
            "tag-2:9",
            "tag-3:7"
        ]
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)


    def testMapDispatchCollect(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        input: std.Counter()
        disp : flow.Dispatch()
        coll : flow.Collect()
        tag1: text.PrefixString(prefix="tag1-")
        tag2: text.PrefixString(prefix="tag2-")
        tag3: text.PrefixString(prefix="tag3-")

        input.integer > disp.token
        disp.token > tag1.in
        disp.token > tag2.in
        disp.token > tag3.in
        tag1.out > coll.token
        tag2.out > coll.token
        tag3.out > coll.token
        coll.token > snk.token
        """
        actual = self._run_test(script, 50)
        pairs = [x.split('-') for x in actual]
        tags = [p[0] for p in pairs]
        values = [int(p[1]) for p in pairs]
        assert (set(values) == set(range(1, len(actual)+1)))
        print tags
        assert set(tags) == set(["tag1", "tag2", "tag3"])

    def testMapDispatchDict(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        dd : flow.DispatchDict(mapping={"t1": &tag1.in, "t2": &tag2.in, "t3": &tag3.in})
        tag1: text.PrefixString(prefix="tag-1:")
        tag2: text.PrefixString(prefix="tag-2:")
        tag3: text.PrefixString(prefix="tag-3:")
        coll : flow.Alternate(order=[&tag1.out, &tag2.out, &tag3.out])
        {"t1": 1, "t2": 2, "t3": 3} > dd.dict
        dd.token > tag1.in
        dd.token > tag2.in
        dd.token > tag3.in
        dd.default > voidport
        tag1.out > coll.token
        tag2.out > coll.token
        tag3.out > coll.token
        coll.token > snk.token
        """

        expected = [
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
        ]
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)

    def testMapCollectCompleteDict(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        dd : flow.DispatchDict(mapping={"t1": &tag1.in, "t2": &tag2.in, "t3": &tag3.in})
        tag1: text.PrefixString(prefix="tag-1:")
        tag2: text.PrefixString(prefix="tag-2:")
        tag3: text.PrefixString(prefix="tag-3:")
        cd : flow.CollectCompleteDict(mapping={"t1": &tag2.out, "t2": &tag3.out, "t3": &tag1.out})
        {"t1": 1, "t2": 2, "t3": 3} > dd.dict
        dd.token > tag1.in
        dd.token > tag2.in
        dd.token > tag3.in
        dd.default > voidport
        tag1.out > cd.token
        tag2.out > cd.token
        tag3.out > cd.token
        cd.dict > snk.token
        """
        actual = self._run_test(script, 50)
        expected = [{u't2': 'tag-3:3', u't3': 'tag-1:1', u't1': 'tag-2:2'}]*len(actual)
        self.assert_lists_equal(expected, actual)

    @pytest.mark.skip # xfail, but slow
    def testMapComponentPort(self):
        script = r"""
        component Dummy() in -> out {
            identity : std.Identity()
            .in > identity.token
            identity.token > .out
        }
        snk : test.Sink(store_tokens=1, quiet=1)
        dummy : Dummy()
        cdict : flow.CollectCompleteDict(mapping={"dummy":&dummy.out})
        1 > dummy.in
        dummy.out > cdict.token
        cdict.dict > snk.token
        """
        actual = self._run_test(script, 10)
        expected = [{u'dummy': 1}]*len(actual)
        self.assert_lists_equal(expected, actual)


    @pytest.mark.skip # xfail, but slow
    def testMapComponentInternalPort(self):
        script = r"""
        component Dummy() in -> out {
            # Works with &foo.token or "foo.token" if constant has label :foo
            cdict : flow.CollectCompleteDict(mapping={"dummy":&.in})

            .in > cdict.token
            cdict.dict > .out
        }
        snk : test.Sink(store_tokens=1, quiet=1)
        dummy : Dummy()
        1 > dummy.in
        dummy.out > snk.token
        """
        actual = self._run_test(script, 10)
        expected = [{u'dummy': 1}]*len(actual)
        self.assert_lists_equal(expected, actual)