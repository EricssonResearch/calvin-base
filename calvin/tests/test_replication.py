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


rt1 = None
rt2 = None
rt3 = None
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

def get_runtime(n=1):
    import random
    runtimes = [rt1, rt2, rt3]
    random.shuffle(runtimes)
    return runtimes[:n]
  
def setup_module(module):
    global rt1, rt2, rt3
    global request_handler
    global test_type

    request_handler = RequestHandler()
    test_type, [rt1, rt2, rt3] = helpers.setup_test_type(request_handler)


def teardown_module(module):
    global rt1
    global rt2
    global rt3
    global test_type
    global request_handler

    helpers.teardown_test_type(request_handler, [rt1, rt2, rt3], test_type)


class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.rt1 = rt1
        self.rt2 = rt2
        self.rt3 = rt3

    def assert_lists_equal(self, expected, actual, min_length=5):
        self.assertTrue(len(actual) >= min_length, "Received data too short (%d), need at least %d" % (len(actual), min_length))
        self._assert_lists_equal(expected, actual)

    def _assert_lists_equal(self, expected, actual):
        assert actual
        assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True) 
        
    def compile_script(self, script, name):
        # Instead of rewriting tests after compiler.compile_script changed
        # from returning app_info, errors, warnings to app_info, issuetracker
        # use this stub in tests to keep old behaviour
        app_info, issuetracker = compiler.compile_script(script, name)
        return app_info, issuetracker.errors(), issuetracker.warnings()

    def wait_for_migration(self, runtime, actors, retries=20):
        retry = 0
        if not isinstance(actors, list):
            actors = [ actors ]
        while retry < retries:
            try:
                current = request_handler.get_actors(runtime)
                if set(actors).issubset(set(current)):
                    break
                else:
                    _log.info("Migration not finished, retrying in %f" % (retry * 0.1,))
                    retry += 1
                    time.sleep(retry * 0.1)
            except Exception as e:
                _log.info("Migration not finished %s, retrying in %f" % (str(e), retry * 0.1,))
                retry += 1
                time.sleep(retry * 0.1)
        if retry == retries:
            _log.info("Migration failed, after %d retires" % (retry,))
            raise Exception("Migration failed")

    def migrate(self, source, dest, actor):
        request_handler.migrate(source, actor, dest.id)
        self.wait_for_migration(dest, [actor])


@pytest.mark.slow
class TestReplication(CalvinTestBase):

    def testSimpleReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            sum   : std.Sum()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-unordered")
            src.integer > sum.integer
            sum.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        asum = d.actor_map['testScript:sum']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, asum)
        asum_sum_first = request_handler.report(self.rt1, asum)
        actual_first = request_handler.report(self.rt1, snk)
        time.sleep(0.5)
        print result
        asum2 = result['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert asum2 in actors
        asum_meta = request_handler.get_actor(self.rt1, asum)
        asum2_meta = request_handler.get_actor(self.rt1, asum2)
        print asum_meta
        print asum2_meta
        for port in asum2_meta['inports']:
            r = request_handler.get_port(self.rt1, asum2, port['id'])
            print port['id'], ': ', r
        for port in asum2_meta['outports']:
            r = request_handler.get_port(self.rt1, asum2, port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        print actual
        asum_sum = request_handler.report(self.rt1, asum)
        asum2_sum = request_handler.report(self.rt1, asum2)
        print asum_sum, asum2_sum
        assert len(actual) > len(actual_first)
        # This works since local is so fast, otherwise check how it is done in testSimpleRemoteReplication
        assert asum_sum > asum_sum_first
        assert asum2_sum > asum_sum_first
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert asum not in actors
        assert asum2 not in actors
        assert src not in actors
        assert snk not in actors

    def testSimpleRemoteReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            sum   : std.Sum()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-unordered")
            src.integer > sum.integer
            sum.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        asum = d.actor_map['testScript:sum']
        snk = d.actor_map['testScript:snk']

        asum_sum_first = [request_handler.report(self.rt1, asum)]
        result = request_handler.replicate(self.rt1, asum, self.rt2.id)
        asum_sum_first.append(request_handler.report(self.rt1, asum))
        actual_first = request_handler.report(self.rt1, snk)
        time.sleep(0.5)
        print result
        asum2 = result['actor_id']
        actors = request_handler.get_actors(self.rt2)
        assert asum2 in actors
        asum_meta = request_handler.get_actor(self.rt1, asum)
        asum2_meta = request_handler.get_actor(self.rt2, asum2)
        print asum_meta
        print asum2_meta
        for port in asum2_meta['inports']:
            r = request_handler.get_port(self.rt2, asum2, port['id'])
            print port['id'], ': ', r
        for port in asum2_meta['outports']:
            r = request_handler.get_port(self.rt2, asum2, port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        print actual
        asum_sum = request_handler.report(self.rt1, asum)
        asum2_sum = request_handler.report(self.rt2, asum2)
        print asum_sum, asum2_sum
        assert len(actual) > len(actual_first)
        assert asum_sum > asum_sum_first[0]
        assert asum_sum > asum_sum_first[1]
        assert asum2_sum > asum_sum_first[0]

        # Find first cumsum that is different and then that the replicated actor is beyond that
        cumsum = helpers.expected_sum(10000)
        i = [i for i,v in enumerate(actual) if cumsum[i] != v]
        assert cumsum[i[0]] < asum2_sum
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1) + request_handler.get_actors(self.rt2)
        assert asum not in actors
        assert asum2 not in actors
        assert src not in actors
        assert snk not in actors

    def testManyRemoteReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            sum   : std.Sum()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-unordered")
            src.integer > sum.integer
            sum.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        asum = d.actor_map['testScript:sum']
        snk = d.actor_map['testScript:snk']

        asum_sum_first = [request_handler.report(self.rt1, asum)]
        rts =[self.rt2.id, self.rt3.id]
        result=[]
        for i in range(5):
            result.append(request_handler.replicate(self.rt1, asum, rts[i%2]))
        asum_sum_first.append(request_handler.report(self.rt1, asum))
        actual_first = request_handler.report(self.rt1, snk)
        time.sleep(0.5)
        print result
        asum2 = [r['actor_id'] for r in result]
        actors = [request_handler.get_actors(self.rt2), request_handler.get_actors(self.rt3)]
        for i in range(5):
            assert asum2[i] in actors[i%2]
        asum_meta = request_handler.get_actor(self.rt1, asum)
        asum2_meta = request_handler.get_actor(self.rt2, asum2[4])
        print asum_meta
        print asum2_meta
        for port in asum2_meta['inports']:
            r = request_handler.get_port(self.rt2, asum2[4], port['id'])
            print port['id'], ': ', r
        for port in asum2_meta['outports']:
            r = request_handler.get_port(self.rt2, asum2[4], port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        print actual
        asum_sum = request_handler.report(self.rt1, asum)
        asum2_sum = []
        rts =[self.rt2, self.rt3]
        for i in range(5):
            asum2_sum.append(request_handler.report(rts[i%2], asum2[i]))
        print asum_sum, asum2_sum
        assert len(actual) > len(actual_first)
        assert asum_sum > asum_sum_first[0]
        assert asum_sum > asum_sum_first[1]
        for i in range(5):
            assert asum2_sum[i] > asum_sum_first[0]
        # Find first cumsum that is different and then that the replicated actor is beyond that
        cumsum = helpers.expected_sum(10000)
        i = [i for i,v in enumerate(actual) if cumsum[i] != v]
        for ii in range(5):
            assert cumsum[i[0]] < asum2_sum[ii]
        helpers.destroy_app(d)
        time.sleep(1)
        actors = (request_handler.get_actors(self.rt1) + request_handler.get_actors(self.rt2) +
                    request_handler.get_actors(self.rt3))
        assert asum not in actors
        for i in range(5):
            assert asum2[i] not in actors
        assert src not in actors
        assert snk not in actors

    def testSimpleTagReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            sum   : std.Sum()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > sum.integer
            sum.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        asum = d.actor_map['testScript:sum']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, asum)
        asum_sum_first = request_handler.report(self.rt1, asum)
        actual_first = request_handler.report(self.rt1, snk)
        time.sleep(0.5)
        print result
        asum2 = result['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert asum2 in actors
        asum_meta = request_handler.get_actor(self.rt1, asum)
        asum2_meta = request_handler.get_actor(self.rt1, asum2)
        print asum_meta
        print asum2_meta
        for port in asum2_meta['inports']:
            r = request_handler.get_port(self.rt1, asum2, port['id'])
            print port['id'], ': ', r
        for port in asum2_meta['outports']:
            r = request_handler.get_port(self.rt1, asum2, port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        asum_sum = request_handler.report(self.rt1, asum)
        asum2_sum = request_handler.report(self.rt1, asum2)
        print asum_sum, asum2_sum
        assert len(actual) > len(actual_first)
        # This works since local is so fast, otherwise check how it is done in testSimpleRemoteReplication
        assert asum_sum > asum_sum_first
        assert asum2_sum > asum_sum_first
        id1 = asum_meta['outports'][0]['id']
        id2 = asum2_meta['outports'][0]['id']
        assert [a[id1] for a in actual if id1 in a]
        assert [a[id2] for a in actual if id2 in a]
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert asum not in actors
        assert asum2 not in actors
        assert src not in actors
        assert snk not in actors

    def testSimpleFanOutTagReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            sum   : std.Sum()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="fanout")
            snk.token(routing="collect-tagged")
            src.integer > sum.integer
            sum.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        asum = d.actor_map['testScript:sum']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, asum)
        asum_sum_first = request_handler.report(self.rt1, asum)
        actual_first = request_handler.report(self.rt1, snk)
        time.sleep(0.5)
        print result
        asum2 = result['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert asum2 in actors
        asum_meta = request_handler.get_actor(self.rt1, asum)
        asum2_meta = request_handler.get_actor(self.rt1, asum2)
        print asum_meta
        print asum2_meta
        for port in asum2_meta['inports']:
            r = request_handler.get_port(self.rt1, asum2, port['id'])
            print port['id'], ': ', r
        for port in asum2_meta['outports']:
            r = request_handler.get_port(self.rt1, asum2, port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        asum_sum = request_handler.report(self.rt1, asum)
        asum2_sum = request_handler.report(self.rt1, asum2)
        print asum_sum, asum2_sum
        assert len(actual) > len(actual_first)
        # This works since local is so fast, otherwise check how it is done in testSimpleRemoteReplication
        assert asum_sum > asum_sum_first
        assert asum2_sum > asum_sum_first
        id1 = asum_meta['outports'][0]['id']
        id2 = asum2_meta['outports'][0]['id']
        a1 = [a[id1] for a in actual if id1 in a]
        a2 = [a[id2] for a in actual if id2 in a]
        print a1
        print a2
        assert a1
        assert a2
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert asum not in actors
        assert asum2 not in actors
        assert src not in actors
        assert snk not in actors

    def testMultiPortReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src1    : std.FiniteCounter(start=0)
            src2    : std.FiniteCounter(start=10000)
            alt   : std.Alternate()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src1.integer(routing="fanout")
            src2.integer(routing="random")
            snk.token(routing="collect-tagged")
            src1.integer > alt.token_1
            src2.integer > alt.token_2
            alt.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src1 = d.actor_map['testScript:src1']
        src2 = d.actor_map['testScript:src2']
        alt = d.actor_map['testScript:alt']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, alt)
        actual_first = request_handler.report(self.rt1, snk)
        time.sleep(1)
        print result
        alt2 = result['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert alt2 in actors
        alt_meta = request_handler.get_actor(self.rt1, alt)
        alt2_meta = request_handler.get_actor(self.rt1, alt2)
        print alt_meta
        print alt2_meta
        for port in alt2_meta['inports']:
            r = request_handler.get_port(self.rt1, alt2, port['id'])
            print port['id'], ': ', r
        for port in alt2_meta['outports']:
            r = request_handler.get_port(self.rt1, alt2, port['id'])
            print port['id'], ': ', r

        id1 = alt_meta['outports'][0]['id']
        id2 = alt2_meta['outports'][0]['id']

        for i in range(10):
            actual = request_handler.report(self.rt1, snk)
            a1 = [a[id1] for a in actual if id1 in a]
            a2 = [a[id2] for a in actual if id2 in a]
            if len(a2) > 15:
                break
            time.sleep(0.1)
        print a1
        print a2
        h1 = [a for a in a1 if a >9999]
        h2 = [a for a in a2 if a >9999]
        l1 = [a for a in a1 if a <10000]
        l2 = [a for a in a2 if a <10000]
        print "h1", h1
        print "h2", h2
        print "l1", l1
        print "l2", l2
        assert len(a1) > 15
        assert len(a2) > 15
        assert len(h1) > 15
        assert len(h2) > 15
        assert len(l1) > 15
        assert len(l2) > 15
        assert l1 == range(l1[0], l1[-1]+1)
        assert l2 == range(l2[0], l2[-1]+1)
        assert not (set(h1) & set(h2))
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert alt not in actors
        assert alt2 not in actors
        assert src1 not in actors
        assert src2 not in actors
        assert snk not in actors

    def testMultiActorReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src1    : std.FiniteCounter(start=0)
            src2    : std.FiniteCounter(start=10000, replicate_mult=true)
            alt   : std.Alternate()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src1.integer(routing="fanout")
            src2.integer(routing="random")
            alt.token_2(routing="collect-unordered")
            snk.token(routing="collect-tagged")
            src1.integer > alt.token_1
            src2.integer > alt.token_2
            alt.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src1 = d.actor_map['testScript:src1']
        src2 = d.actor_map['testScript:src2']
        alt = d.actor_map['testScript:alt']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, alt)
        result_src = request_handler.replicate(self.rt1, src2)
        actual_first = request_handler.report(self.rt1, snk)
        time.sleep(1)
        print result, result_src
        alt2 = result['actor_id']
        src22 = result_src['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert alt2 in actors
        alt_meta = request_handler.get_actor(self.rt1, alt)
        alt2_meta = request_handler.get_actor(self.rt1, alt2)
        print alt_meta
        print alt2_meta
        for port in alt2_meta['inports']:
            r = request_handler.get_port(self.rt1, alt2, port['id'])
            print port['id'], ': ', r
        for port in alt2_meta['outports']:
            r = request_handler.get_port(self.rt1, alt2, port['id'])
            print port['id'], ': ', r

        id1 = alt_meta['outports'][0]['id']
        id2 = alt2_meta['outports'][0]['id']

        for i in range(10):
            actual = request_handler.report(self.rt1, snk)
            a1 = [a[id1] for a in actual if id1 in a]
            a2 = [a[id2] for a in actual if id2 in a]
            if len(a2) > 15:
                break
            time.sleep(0.1)
        print a1
        print a2
        h1 = [a for a in a1 if a >9999 and a<20000]
        h2 = [a for a in a2 if a >9999 and a<20000]
        hh1 = [a for a in a1 if a >19999]
        hh2 = [a for a in a2 if a >19999]
        l1 = [a for a in a1 if a <10000]
        l2 = [a for a in a2 if a <10000]
        print "*h1", h1
        print "*h2", h2
        print "*hh1", hh1
        print "*hh2", hh2
        print "*l1", l1
        print "*l2", l2
        assert len(a1) > 15
        assert len(a2) > 15
        assert len(h1) > 15
        assert len(h2) > 15
        assert len(hh1) > 15
        assert len(hh2) > 15
        assert len(l1) > 15
        assert len(l2) > 15
        assert l1 == range(l1[0], l1[-1]+1)
        assert l2 == range(l2[0], l2[-1]+1)
        assert not (set(h1) & set(h2))
        assert not (set(hh1) & set(hh2))
        hh = sorted(hh1+hh2)
        assert hh[:-7] == range(hh[0], hh[-7])
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert alt not in actors
        assert alt2 not in actors
        assert src1 not in actors
        assert src2 not in actors
        assert src22 not in actors
        assert snk not in actors

    def testScaleOut1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.FiniteCounter(start=10000, replicate_mult=true)
            mid   : std.Identity()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            mid.token[in](routing="collect-unordered")
            mid.token[out](routing="random")
            snk.token(routing="collect-tagged")
            src.integer > mid.token
            mid.token > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        mid = d.actor_map['testScript:mid']
        snk = d.actor_map['testScript:snk']

        srcr = []
        midr = []

        for i in range(10):
            result_src = request_handler.replicate(self.rt1, src)
            srcr.append(result_src['actor_id'])
            if i % 5 == 0:
                result_mid = request_handler.replicate(self.rt1, mid)
                midr.append(result_mid['actor_id'])

        last_mid_meta = request_handler.get_actor(self.rt1, midr[-1])
        mid_port_id = last_mid_meta['outports'][0]['id']
        for i in range(10):
            actual = request_handler.report(self.rt1, snk)
            a_last = [a[mid_port_id] for a in actual if mid_port_id in a and a[mid_port_id]>110000]
            
            if len(a_last) > 10:
                break
            time.sleep(0.1)
        ports = set([])
        map(lambda a: ports.update(a.keys()), actual)
        assert len(ports) == (len(midr) + 1)
        actual_mids = {}
        for p in ports:
            di = [a[p] for a in actual if p in a]
            dd = {}
            map(lambda a: dd.setdefault(int(a)/10000,[]).append(a), di)
            actual_mids[p] = dd
            assert all(dd.values())
        for p in ports:
            print p
            for k, v in actual_mids[p].items():
                print "\t", k, ": ", str(v)

        for i in range(1,12):
            sets = [set(vv[i]) for p, vv in actual_mids.items()]
            assert not set.intersection(*sets)

        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert src not in actors
        assert mid not in actors
        assert snk not in actors
        assert not (set(srcr) & set(actors))
        assert not (set(midr) & set(actors))

    def testScaleOut2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.FiniteCounter(start=10000, replicate_mult=true)
            mid   : std.Identity()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            mid.token[in](routing="collect-unordered")
            mid.token[out](routing="random")
            snk.token(routing="collect-tagged")
            src.integer > mid.token
            mid.token > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        mid = d.actor_map['testScript:mid']
        snk = d.actor_map['testScript:snk']

        srcrf = []
        midrf = []

        for i in range(10):
            result_src = request_handler.async_replicate(self.rt1, src, self.rt2.id)
            srcrf.append(result_src)
            if i % 5 == 0:
                result_mid = request_handler.async_replicate(self.rt1, mid, self.rt3.id)
                midrf.append(result_mid)

        srcr = map(lambda x: request_handler.async_response(x)['actor_id'], srcrf)
        midr = map(lambda x: request_handler.async_response(x)['actor_id'], midrf)

        last_mid_meta = request_handler.get_actor(self.rt1, midr[-1])
        mid_port_id = last_mid_meta['outports'][0]['id']
        for i in range(10):
            actual = request_handler.report(self.rt1, snk)
            a_last = [a[mid_port_id] for a in actual if mid_port_id in a and a[mid_port_id]>110000]
            if len(a_last) > 10:
                break
            time.sleep(0.1)

        mid_meta = map(lambda x: (x, request_handler.get_actor(self.rt1, x)), [mid] + midr)
        # actor_id, inport, outport
        mid_ports = [(x[0],
                      (x[1]['inports'][0]['id'], request_handler.get_port(self.rt1, x[0], x[1]['inports'][0]['id'])),
                      (x[1]['outports'][0]['id'], request_handler.get_port(self.rt1, x[0], x[1]['outports'][0]['id'])))
                      for x in mid_meta]
        mid_peer_ports = [(x[0], (x[1][0], x[1][1]['peers']), (x[2][0], x[2][1]['peers'])) for x in mid_ports]
        import pprint
        pprint.pprint(mid_peer_ports, width=250)

        for a in mid_peer_ports:
            assert len(a[1][1]) == 11
            assert len(a[2][1]) == 1

        ports = set([])
        map(lambda a: ports.update(a.keys()), actual)
        assert len(ports) == (len(midr) + 1)
        actual_mids = {}
        for p in ports:
            di = [a[p] for a in actual if p in a]
            dd = {}
            map(lambda a: dd.setdefault(int(a)/10000,[]).append(a), di)
            actual_mids[p] = dd
            assert all(dd.values())
        for p in ports:
            print p
            for k, v in actual_mids[p].items():
                print "\t", k, ": ", str(v)

        for i in range(1,12):
            sets = [set(vv[i]) for p, vv in actual_mids.items() if i in vv]
            assert not set.intersection(*sets)

        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1) + request_handler.get_actors(self.rt2) + request_handler.get_actors(self.rt3)
        assert src not in actors
        assert mid not in actors
        assert snk not in actors
        assert not (set(srcr) & set(actors))
        assert not (set(midr) & set(actors))
