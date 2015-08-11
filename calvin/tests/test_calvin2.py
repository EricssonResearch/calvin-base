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

def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)

rt1 = None
rt2 = None
rt3 = None

def setup_module(module):
    global rt1
    global rt2
    global rt3
    rt1 = dispatch_node("calvinip://localhost:5000", "http://localhost:5003")
    rt2 = dispatch_node("calvinip://localhost:5001", "http://localhost:5004")
    rt3 = dispatch_node("calvinip://localhost:5002", "http://localhost:5005")
    time.sleep(.4)
    utils.peer_setup(rt1, ["calvinip://localhost:5001", "calvinip://localhost:5002"])
    utils.peer_setup(rt2, ["calvinip://localhost:5000", "calvinip://localhost:5002"])
    utils.peer_setup(rt3, ["calvinip://localhost:5000", "calvinip://localhost:5001"])
    time.sleep(.4)

def teardown_module(module):
    global rt1
    global rt2
    global rt3
    utils.quit(rt1)
    utils.quit(rt2)
    utils.quit(rt3)
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

@pytest.mark.essential
class TestConnections(CalvinTestBase):

    @pytest.mark.slow
    def testLocalSourceSink(self):
        src = utils.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(.5)

        actual = utils.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

    def testMigrateSink(self):
        src = utils.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(.4)
        utils.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(.6)

        actual = utils.report(self.rt2, snk)
        self.assert_lists_equal(range(1, 10), actual)

    def testMigrateSource(self):
        src = utils.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(.4)
        utils.migrate(self.rt1, src, self.rt2.id)
        time.sleep(.6)

        actual = utils.report(self.rt1, snk)
        self.assert_lists_equal(range(1, 10), actual)

    def testTwoStepMigrateSinkSource(self):
        src = utils.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(1)
        utils.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(1)
        utils.migrate(self.rt1, src, self.rt2.id)
        time.sleep(1)

        actual = utils.report(self.rt2, snk)
        self.assert_lists_equal(range(1,15), actual, min_length=10)

    def testTwoStepMigrateSourceSink(self):
        src = utils.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(1)
        utils.migrate(self.rt1, src, self.rt2.id)
        utils.report(self.rt1, snk)
        time.sleep(1)
        utils.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(1)

        actual = utils.report(self.rt2, snk)
        self.assert_lists_equal(range(1,20), actual, min_length=15)

@pytest.mark.essential
class TestScripts(CalvinTestBase):

    @pytest.mark.slow
    def testInlineScript(self):
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        snk = d.actor_map['simple:snk']

        actual = utils.report(self.rt1, (snk))
        self.assert_lists_equal(range(1, 20), actual)

    @pytest.mark.slow
    def testFileScript(self):
        scriptname = 'test1'
        scriptfile = absolute_filename("scripts/%s.calvin" % (scriptname, ))
        app_info, errors, warnings = compiler.compile_file(scriptfile)
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        src = d.actor_map['%s:src' % scriptname]
        snk = d.actor_map['%s:snk' % scriptname]

        actual = utils.report(self.rt1, snk)
        self.assert_lists_equal(range(1, 20), actual)


class TestStateMigration(CalvinTestBase):

    def testSimpleState(self):
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        utils.migrate(self.rt1, csum, self.rt2.id)
        time.sleep(1)

        actual = utils.report(self.rt1, snk)
        expected = [sum(range(i+1)) for i in range(1,10)]

        self.assert_lists_equal(expected, actual)


@pytest.mark.slow
@pytest.mark.essential
class TestAppLifeCycle(CalvinTestBase):

    def testAppDestructionOneRemote(self):
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        utils.migrate(self.rt1, csum, self.rt2.id)
        time.sleep(1)

        actual = utils.report(self.rt1, snk)
        expected = [sum(range(i+1)) for i in range(1,10)]
        self.assert_lists_equal(expected, actual)
        utils.delete_application(self.rt1, d.app_id)
        time.sleep(0.5)
        self.assertIsNone(utils.get_actor(self.rt1, src))
        self.assertIsNone(utils.get_actor(self.rt1, csum))
        self.assertIsNone(utils.get_actor(self.rt1, snk))
        self.assertIsNone(utils.get_application(self.rt1, d.app_id))

    def testAppDestructionAllRemote(self):
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)
        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        utils.migrate(self.rt1, src, self.rt2.id)
        utils.migrate(self.rt1, csum, self.rt2.id)
        utils.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(1)

        actual = utils.report(self.rt2, snk)
        expected = [sum(range(i+1)) for i in range(1,10)]
        self.assert_lists_equal(expected, actual)
        utils.delete_application(self.rt1, d.app_id)
        time.sleep(0.5)
        self.assertIsNone(utils.get_actor(self.rt1, src))
        self.assertIsNone(utils.get_actor(self.rt1, csum))
        self.assertIsNone(utils.get_actor(self.rt1, snk))
        self.assertIsNone(utils.get_application(self.rt1, d.app_id))


@pytest.mark.essential
class TestEnabledToEnabledBug(CalvinTestBase):

    def test10(self):
        # Two actors, doesn't seem to trigger the bug
        src = utils.new_actor(self.rt1, 'std.Counter', 'src')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        time.sleep(0.1)

        actual = utils.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

    def test11(self):
        # Same as test10, but scripted
        script = """
            src : std.Counter()
            snk : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.06)

        snk = d.actor_map['simple:snk']
        actual = utils.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

    def test20(self):
        src = utils.new_actor(self.rt1, 'std.Counter', 'src')
        ity = utils.new_actor(self.rt1, 'std.Identity', 'ity')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, snk, 'token', self.rt1.id, ity, 'token')
        utils.connect(self.rt1, ity, 'token', self.rt1.id, src, 'integer')

        time.sleep(0.2)

        actual = utils.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 11), actual)

    def test21(self):
        src = utils.new_actor(self.rt1, 'std.Counter', 'src')
        ity = utils.new_actor(self.rt2, 'std.Identity', 'ity')
        snk = utils.new_actor_wargs(self.rt3, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt3, snk, 'token', self.rt2.id, ity, 'token')
        utils.connect(self.rt2, ity, 'token', self.rt1.id, src, 'integer')

        time.sleep(0.1)

        actual = utils.report(self.rt3, snk)

        self.assert_lists_equal(range(1, 11), actual)

    def test22(self):
        src = utils.new_actor(self.rt1, 'std.Counter', 'src')
        ity = utils.new_actor(self.rt2, 'std.Identity', 'ity')
        snk = utils.new_actor_wargs(self.rt3, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt2, ity, 'token', self.rt1.id, src, 'integer')
        utils.connect(self.rt3, snk, 'token', self.rt2.id, ity, 'token')

        time.sleep(0.1)

        actual = utils.report(self.rt3, snk)

        self.assert_lists_equal(range(1, 10), actual)

    def test25(self):
        src = utils.new_actor(self.rt1, 'std.Counter', 'src')
        ity = utils.new_actor(self.rt1, 'std.Identity', 'ity')
        snk = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        utils.connect(self.rt1, ity, 'token', self.rt1.id, src, 'integer')
        utils.connect(self.rt1, snk, 'token', self.rt1.id, ity, 'token')

        time.sleep(0.2)

        actual = utils.report(self.rt1, snk)

        self.assert_lists_equal(range(1, 10), actual)

    def test26(self):
        # Same as test20
        script = """
            src : std.Counter()
            ity : std.Identity()
            snk : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > ity.token
            ity.token > snk.token
          """
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.4)

        snk = d.actor_map['simple:snk']
        actual = utils.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

    def test30(self):
        src = utils.new_actor(self.rt1, 'std.Counter', 'src')
        snk1 = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = utils.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)

        utils.set_port_property(self.rt1, src, 'out', 'integer', 'fanout', 2)

        utils.connect(self.rt1, snk1, 'token', self.rt1.id, src, 'integer')
        utils.connect(self.rt1, snk2, 'token', self.rt1.id, src, 'integer')

        time.sleep(0.2)

        actual1 = utils.report(self.rt1, snk1)
        actual2 = utils.report(self.rt1, snk2)

        self.assert_lists_equal(list(range(1, 10)), actual1)
        self.assert_lists_equal(list(range(1, 10)), actual2)

    def test31(self):
        # Verify that fanout defined implicitly in scripts is handled correctly
        script = """
            src : std.Counter()
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            snk2 : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = compiler.compile(script, "test31")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.1)

        snk1 = d.actor_map['test31:snk1']
        snk2 = d.actor_map['test31:snk2']
        actual1 = utils.report(self.rt1, snk1)
        actual2 = utils.report(self.rt1, snk2)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)


@pytest.mark.essential
class TestNullPorts(CalvinTestBase):

    def testVoidActor(self):
        # Verify that the null port of a std.Void actor behaves as expected
        script = """
            src1 : std.Counter()
            src2 : std.Void()
            join : std.Join()
            snk  : io.StandardOut(store_tokens=1, quiet=1)

            src1.integer > join.token_1
            src2.null > join.token_2
            join.token > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testVoidActor")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.4)

        snk = d.actor_map['testVoidActor:snk']
        actual = utils.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

    def testTerminatorActor(self):
        # Verify that the null port of a std.Terminator actor behaves as expected
        script = """
            src  : std.Counter()
            term : std.Terminator()
            snk  : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > term.null
            src.integer > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testTerminatorActor")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testTerminatorActor:snk']
        actual = utils.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

@pytest.mark.essential
class TestCompare(CalvinTestBase):

    def testBadOp(self):
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op="<>")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testBadOp")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.05)

        snk = d.actor_map['testBadOp:snk']
        actual = utils.report(self.rt1, snk)
        expected = [0] * 10

        self.assert_lists_equal(expected, actual)

    def testEqual(self):
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op="=")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testEqual")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.1)

        snk = d.actor_map['testEqual:snk']
        actual = utils.report(self.rt1, snk)
        expected = [x == 5 for x in range(1, 10)]

        self.assert_lists_equal(expected, actual)

    def testGreaterThanOrEqual(self):
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op=">=")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testGreaterThanOrEqual")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.1)

        snk = d.actor_map['testGreaterThanOrEqual:snk']
        actual = utils.report(self.rt1, snk)
        expected = [x >= 5 for x in range(1, 10)]

        self.assert_lists_equal(expected, actual)


@pytest.mark.essential
class TestSelect(CalvinTestBase):

    def testTrue(self):
        script = """
            src   : std.Counter()
            const : std.Constant(data=1, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.true  > snk.token
            route.false > term.null
        """
        app_info, errors, warnings = compiler.compile(script, "testTrue")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.2)

        snk = d.actor_map['testTrue:snk']
        actual = utils.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

    def testFalse(self):
        script = """
            src   : std.Counter()
            const : std.Constant(data=0, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.true  > term.null
            route.false > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testFalse")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testFalse:snk']
        actual = utils.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

    def testBadSelect(self):
        script = """
            src   : std.Counter()
            const : std.Constant(data=2, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.true  > term.null
            route.false > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testBadSelect")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testBadSelect:snk']
        actual = utils.report(self.rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)


@pytest.mark.essential
class TestDeselect(CalvinTestBase):

    def testDeselectTrue(self):
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=-1)
            const_1 : std.Constant(data=1, n=-1)
            comp    : std.Compare(op="<=")
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.false
            const_1.token > ds.true
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testDeselectTrue")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testDeselectTrue:snk']
        actual = utils.report(self.rt1, snk)
        expected = [1] * 5 + [0] * 5

        self.assert_lists_equal(expected, actual, min_length=10)

    def testDeselectFalse(self):
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=-1)
            const_1 : std.Constant(data=1, n=-1)
            comp    : std.Compare(op="<=")
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.true
            const_1.token > ds.false
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testDeselectFalse")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testDeselectFalse:snk']
        actual = utils.report(self.rt1, snk)
        expected = [0] * 5 + [1] * 5

        self.assert_lists_equal(expected, actual, min_length=10)

    def testDeselectBadSelect(self):
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=11)
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.false
            src.integer > ds.true
            const_0.token > const_5.in
            const_5.out > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testDeselectBadSelect")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testDeselectBadSelect:snk']
        actual = utils.report(self.rt1, snk)
        expected = [0] * 10

        self.assert_lists_equal(expected, actual, min_length=10)


@pytest.mark.essential
class TestLineJoin(CalvinTestBase):

    def testBasicJoin(self):
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
        app_info, errors, warnings = compiler.compile(script, "testBasicJoin")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(1)

        snk = d.actor_map['testBasicJoin:snk']
        actual = utils.report(self.rt1, snk)
        with open(datafile, "r") as fp:
            expected = ["\n".join([l.rstrip() for l in fp.readlines()])]

        self.assert_lists_equal(expected, actual, min_length=1)

    @pytest.mark.xfail
    def testCustomTriggerJoin(self):
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
        app_info, errors, warnings = compiler.compile(script, "testCustomTriggerJoin")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testCustomTriggerJoin:snk']
        actual = utils.report(self.rt1, snk)
        with open(datafile, "r") as fp:
            expected = [l.rstrip() for l in fp.readlines()]
            expected = ['\n'.join(expected[:4]), '\n'.join(expected[4:])]

        self.assert_lists_equal(expected, actual, min_length=2)

    @pytest.mark.xfail
    def testEmptyStringTriggerJoin(self):
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
        app_info, errors, warnings = compiler.compile(script, "testCustomTriggerJoin")
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testCustomTriggerJoin:snk']
        actual = utils.report(self.rt1, snk)
        with open(datafile, "r") as fp:
            expected = [l.rstrip() for l in fp.readlines()]
            expected = ['\n'.join(expected[:10]), '\n'.join(expected[10:])]

        self.assert_lists_equal(expected, actual, min_length=2)



@pytest.mark.essential
class TestRegex(CalvinTestBase):

    def testRegexMatch(self):
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.null
        """
        app_info, errors, warnings = compiler.compile(script, "testRegexMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexMatch:snk']
        actual = utils.report(self.rt1, snk)
        expected = ["24.1632"]

        self.assert_lists_equal(expected, actual, min_length=1)


    def testRegexNoMatch(self):
        script = """
            src   : std.Constant(data="x24.1632", n=1)
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.null
        """
        app_info, errors, warnings = compiler.compile(script, "testRegexNoMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexNoMatch:snk']
        actual = utils.report(self.rt1, snk)
        expected = ["x24.1632"]

        self.assert_lists_equal(expected, actual, min_length=1)

    def testRegexCapture(self):
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.null
        """
        app_info, errors, warnings = compiler.compile(script, "testRegexCapture")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexCapture:snk']
        actual = utils.report(self.rt1, snk)
        expected = ["24"]

        self.assert_lists_equal(expected, actual, min_length=1)

    def testRegexMultiCapture(self):
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.(\d+)")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.null
        """
        app_info, errors, warnings = compiler.compile(script, "testRegexMultiCapture")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexMultiCapture:snk']
        actual = utils.report(self.rt1, snk)
        expected = ["24"]

        self.assert_lists_equal(expected, actual, min_length=1)


    def testRegexCaptureNoMatch(self):
        script = """
            src   : std.Constant(data="x24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.null
        """
        app_info, errors, warnings = compiler.compile(script, "testRegexCaptureNoMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testRegexCaptureNoMatch:snk']
        actual = utils.report(self.rt1, snk)
        expected = ["x24.1632"]

        self.assert_lists_equal(expected, actual, min_length=1)

@pytest.mark.essential
class TestConstantAsArguments(CalvinTestBase):

    def testConstant(self):
        script = """
            define FOO = 42
            src   : std.Constant(data=FOO, n=10)
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testConstant")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstant:snk']
        actual = utils.report(self.rt1, snk)
        expected = [42]*10

        self.assert_lists_equal(expected, actual, min_length=10)

    def testConstantRecursive(self):
        script = """
            define FOO = BAR
            define BAR = 42
            src   : std.Constant(data=FOO, n=10)
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testConstantRecursive")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstantRecursive:snk']
        actual = utils.report(self.rt1, snk)
        expected = [42]*10

        self.assert_lists_equal(expected, actual, min_length=10)


@pytest.mark.essential
class TestConstantOnPort(CalvinTestBase):

    def testLiteralOnPort(self):
        script = """
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            42 > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testLiteralOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testLiteralOnPort:snk']
        actual = utils.report(self.rt1, snk)
        expected = [42]*10

        self.assert_lists_equal(expected, actual, min_length=10)

    def testConstantOnPort(self):
        script = """
            define FOO = "Hello"
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testConstantOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstantOnPort:snk']
        actual = utils.report(self.rt1, snk)
        expected = ["Hello"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

    def testConstantRecursiveOnPort(self):
        script = """
            define FOO = BAR
            define BAR = "yay"
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "testConstantRecursiveOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk = d.actor_map['testConstantRecursiveOnPort:snk']
        actual = utils.report(self.rt1, snk)
        expected = ["yay"]*10

        self.assert_lists_equal(expected, actual, min_length=10)

