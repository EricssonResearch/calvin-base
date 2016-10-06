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
        cumsum = helpers.expected_sum(1000)
        i = [i for i,v in enumerate(actual) if cumsum[i] != v]
        assert cumsum[i[0]] < asum2_sum
        helpers.destroy_app(d)

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
        cumsum = helpers.expected_sum(1000)
        i = [i for i,v in enumerate(actual) if cumsum[i] != v]
        for ii in range(5):
            assert cumsum[i[0]] < asum2_sum[ii]
        helpers.destroy_app(d)
