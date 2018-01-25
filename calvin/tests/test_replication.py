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
import os

from calvin.utilities import calvinconfig
from calvin.csparser import cscompile as compiler
from calvin.Tools import deployer
from calvin.utilities import calvinlogger
from calvin.requests.request_handler import RequestHandler
from . import helpers
from calvin.csparser.dscodegen import calvin_dscodegen


_log = calvinlogger.get_logger(__name__)


def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


rt1 = None
rt2 = None
rt3 = None
runtimes = []
test_type = None
request_handler = None

NBR_RUNTIMES = max(3, int(os.environ.get("CALVIN_NBR_RUNTIMES", 3)))  # At least 3

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

def wait_for_migration(runtime, actors, retries=20):
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

def migrate(source, dest, actor):
    fails = 0
    while fails < 20:
        try:
            request_handler.migrate(source, actor, dest.id)
            break
        except:
            time.sleep(0.1)
            fails += 1
    wait_for_migration(dest, [actor])

def get_runtime(n=1):
    import random
    r = runtimes[:]
    random.shuffle(r)
    return r[:n]
  
def setup_module(module):
    global rt1, rt2, rt3
    global runtimes
    global request_handler
    global test_type

    request_handler = RequestHandler()
    test_type, runtimes = helpers.setup_test_type(request_handler, NBR_RUNTIMES, proxy_storage=True)
    rt1, rt2, rt3 = runtimes[:3]
    print "CREATED", len(runtimes), "RUNTIMES"

def teardown_module(module):
    global runtimes
    global test_type
    global request_handler

    helpers.teardown_test_type(request_handler, runtimes, test_type)


class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.rt1 = rt1
        self.rt2 = rt2
        self.rt3 = rt3
        self.runtimes = runtimes

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


#@pytest.fixture(params=[("rt1", "rt2", "rt3")])
#@pytest.fixture(params=[("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")
#,("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")
#,("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")
#])
@pytest.fixture(params=[("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")])
def rt_order3(request):
    return [globals()[p] for p in request.param]


@pytest.mark.slow
class TestManualReplication(object):
    def testManualNormalReplication(self, rt_order3):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            sum   : std.Sum()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > sum.integer
            sum.integer > snk.token
            rule manual: manual_scaling()
            apply sum: manual
        """

        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response

        src = response['actor_map']['testScript:src']
        asum = response['actor_map']['testScript:sum']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        asum_rt = rt_by_id[response['placement'][asum][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]

        # Move src & snk back to first and place sum on second
        migrate(src_rt, rt1, src)
        migrate(asum_rt, rt2, asum)
        migrate(snk_rt, rt1, snk)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:sum'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        counter = 0
        fails = 0
        while counter < 4 and fails < 20:
            try:
                result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:sum'], dst_id=rt3.id)
                counter += 1
                fails = 0
            except:
                fails += 1
                time.sleep(0.1)
        print "REPLICATED", counter, fails
        assert counter == 4
        replicas = []
        fails = 0
        while len(replicas) < counter and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.1)
        assert len(replicas) == counter
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, asum)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        time.sleep(0.4)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        keys = set([k.keys()[0] for k in actual])
        print keys
        print [k.values()[0] for k in actual]
        result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:sum'], dereplicate=True)
        print "DEREPLICATION RESULT:", result
        time.sleep(0.3)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        print [k.values()[0] for k in actual]
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert asum not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left

    def testManualReplicationDidReplicate(self, rt_order3):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : test.FiniteCounter(start=10000, replicate_mult=true)
            snk   : test.Sink(store_tokens=1, quiet=1)
            snk.token(routing="collect-tagged")
            src.integer > snk.token
            rule manual: manual_scaling()
            apply src: manual
        """

        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response

        src = response['actor_map']['testScript:src']
        snk = response['actor_map']['testScript:snk']

        actor_place = [request_handler.get_actors(r) for r in runtimes]
        src_rt = runtimes[map(lambda x: src in x, actor_place).index(True)]
        snk_rt = runtimes[map(lambda x: snk in x, actor_place).index(True)]

        # Move src & snk back to first
        migrate(src_rt, rt1, src)
        migrate(snk_rt, rt1, snk)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:src'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        counter = 0
        fails = 0
        while counter < 4 and fails < 20:
            try:
                result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:src'], dst_id=rt3.id)
                counter += 1
                fails = 0
            except:
                fails += 1
                time.sleep(0.2)
        print "REPLICATED", counter, fails
        assert counter == 4
        replicas = []
        fails = 0
        while len(replicas) < counter and fails < 40:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:src'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.1)
        assert len(replicas) == counter
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, src)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        time.sleep(0.4)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        keys = set([k.keys()[0] for k in actual])
        print keys
        #print [k.values()[0] for k in actual]
        result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:src'], dereplicate=True)
        print "DEREPLICATION RESULT:", result
        time.sleep(0.3)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        #print [k.values()[0] for k in actual]
        counters = {p:[] for p in set([k.keys()[0] for k in actual])}
        for p in counters.keys():
            counters[p] = [k.values()[0] for k in actual if k.keys()[0] == p]
        #print counters
        countersmm = {p: (min(v), max(v)) for p, v in counters.items()}
        # All min and max belongs in same 10000 range
        assert all([v[0]/10000 == v[1]/10000 for v in countersmm.values()])
        # All 5 10000 ranges included
        assert len(set([v[0]/10000 for v in countersmm.values()])) == 5
        print "MAX MIN", countersmm
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:src'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left

    def testManualReplicationShadow(self, rt_order3):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            shadow : test.FakeShadow()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > shadow.token
            shadow.token > snk.token
            rule manual: manual_scaling()
            apply shadow: manual
        """

        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        rt_by_id = {r.id: r for r in runtimes}

        app_info, issuetracker = compiler.compile_script(script, "testScript")
        if issuetracker.error_count:
            _log.warning("Calvinscript contained errors:")
            _log.warning(issuetracker.formatted_issues())
        #print "APP_INFO", app_info

        deploy_info, ds_issuestracker = calvin_dscodegen(script, "testScript")
        if ds_issuestracker.error_count:
            _log.warning("Deployscript contained errors:")
            _log.warning(ds_issuestracker.formatted_issues())
            deploy_info = None
        elif not deploy_info['requirements']:
            deploy_info = None
        #print "DEPLOY_INFO", deploy_info

        response = request_handler.deploy_app_info(rt1, "testScript", app_info, deploy_info)
        print response

        src = response['actor_map']['testScript:src']
        shadow = response['actor_map']['testScript:shadow']
        snk = response['actor_map']['testScript:snk']

        actor_place = [request_handler.get_actors(r) for r in runtimes]
        src_rt = runtimes[map(lambda x: src in x, actor_place).index(True)]
        shadow_rt = runtimes[map(lambda x: shadow in x, actor_place).index(True)]
        snk_rt = runtimes[map(lambda x: snk in x, actor_place).index(True)]

        # Move src & snk back to first and place shadow on second
        migrate(src_rt, rt1, src)
        migrate(shadow_rt, rt2, shadow)
        migrate(snk_rt, rt1, snk)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:shadow'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        counter = 0
        fails = 0
        while counter < 4 and fails < 20:
            try:
                result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:shadow'], dst_id=rt3.id)
                counter += 1
                fails = 0
            except:
                fails += 1
                time.sleep(0.2)
        print "REPLICATED", counter, fails
        assert counter == 4
        replicas = []
        fails = 0
        while len(replicas) < counter and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:shadow'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.2)
        assert len(replicas) == counter
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, shadow)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        time.sleep(0.4)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        keys = set([k.keys()[0] for k in actual])
        print keys
        print [k.values()[0] for k in actual]
        result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:shadow'], dereplicate=True)
        print "DEREPLICATION RESULT:", result
        time.sleep(0.3)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        print [k.values()[0] for k in actual]
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:shadow'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert shadow not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left

    def testForceMigratingShadow(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            shadow  : test.FakeShadow()
            snk   : test.Sink(store_tokens=1, quiet=false)
            src.integer > shadow.token
            shadow.token > snk.token
        """

        app_info, issuetracker = compiler.compile_script(script, "testScript")
        if issuetracker.error_count:
            _log.warning("Calvinscript contained errors:")
            _log.warning(issuetracker.formatted_issues())
        #print "APP_INFO", app_info

        response = request_handler.deploy_app_info(rt1, "testScript", app_info)
        print response

        src = response['actor_map']['testScript:src']
        shadow = response['actor_map']['testScript:shadow']
        snk = response['actor_map']['testScript:snk']

        migrate(rt1, rt2, shadow)
        time.sleep(0.3)
        migrate(rt2, rt1, shadow)
        time.sleep(0.3)
        migrate(rt1, rt2, shadow)
        time.sleep(0.3)
        actual = request_handler.report(rt1, snk)
        print actual
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert shadow not in actors_left
        assert snk not in actors_left

    def testRequirementMigratingShadow(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            shadow  : test.FakeShadow()
            snk   : test.Sink(store_tokens=1, quiet=false)
            src.integer > shadow.token
            shadow.token > snk.token
            rule anyplace: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test"}])
            apply shadow: anyplace
        """

        rt_by_id = {r.id: r for r in runtimes}

        app_info, issuetracker = compiler.compile_script(script, "testScript")
        if issuetracker.error_count:
            _log.warning("Calvinscript contained errors:")
            _log.warning(issuetracker.formatted_issues())
        #print "APP_INFO", app_info

        deploy_info, ds_issuestracker = calvin_dscodegen(script, "testScript")
        if ds_issuestracker.error_count:
            _log.warning("Deployscript contained errors:")
            _log.warning(ds_issuestracker.formatted_issues())
            deploy_info = None
        elif not deploy_info['requirements']:
            deploy_info = None
        #print "DEPLOY_INFO", deploy_info

        response = request_handler.deploy_app_info(rt1, "testScript", app_info, deploy_info)
        print response

        src = response['actor_map']['testScript:src']
        shadow = response['actor_map']['testScript:shadow']
        snk = response['actor_map']['testScript:snk']

        actor_place = [request_handler.get_actors(r) for r in runtimes]
        shadow_rt = runtimes[map(lambda x: shadow in x, actor_place).index(True)]
        snk_rt = runtimes[map(lambda x: snk in x, actor_place).index(True)]

        # Don't wait, try to race a migration, which should give 503 error and we retry
        migrate(shadow_rt, rt2, shadow)

        # Force back to shadow
        nbr_tokens = len(request_handler.report(snk_rt, snk))
        wait_for_tokens(snk_rt, snk, nbr_tokens+5)
        migrate(rt2, rt1, shadow)

        # No new tokens since shadow just migrate again
        migrate(rt1, rt2, shadow)

        # Landed again as none shadow and produced tokens
        nbr_tokens = len(request_handler.report(snk_rt, snk))
        wait_for_tokens(snk_rt, snk, nbr_tokens+5)

        actual = request_handler.report(snk_rt, snk)
        print actual
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert shadow not in actors_left
        assert snk not in actors_left

    def testDeviceNormalReplication(self, rt_order3):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            sum   : std.Sum()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > sum.integer
            sum.integer > snk.token
            rule device: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & device_scaling(max=6)
            apply sum: device
        """

        global rt2

        nbr_possible = NBR_RUNTIMES - (2 if rt2 == rt_order3[1] else 1)
        rt1 = rt_order3[0]
        rrt2 = rt_order3[1]
        rt3 = rt_order3[2]
        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response

        src = response['actor_map']['testScript:src']
        asum = response['actor_map']['testScript:sum']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        asum_rt = rt_by_id[response['placement'][asum][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]

        # Move src & snk back to first and place sum on second
        migrate(src_rt, rt1, src)
        migrate(asum_rt, rrt2, asum)
        migrate(snk_rt, rt1, snk)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:sum'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        replicas = []
        fails = 0
        while len(replicas) < nbr_possible and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.2)
        assert len(replicas) == nbr_possible
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, asum)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        time.sleep(0.4)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        keys = set([k.keys()[0] for k in actual])
        print keys
        print [k.values()[0] for k in actual]
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        print [k.values()[0] for k in actual]
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert asum not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left

    def testPerformanceOutInReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.01)
            burn   : std.Burn(duration=1.0)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > burn.token
            burn.token > snk.token
            rule single: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            rule scale: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & performance_scaling(alone=true, max=6)
            apply burn: scale
            apply src, snk: single
        """

        global rt1, rt2, rt3

        nbr_possible = NBR_RUNTIMES - 2
        #rt1 = rt_order3[0]
        #rrt2 = rt_order3[1]
        #rt3 = rt_order3[2]
        rrt2 = rt2
        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response

        src = response['actor_map']['testScript:src']
        burn = response['actor_map']['testScript:burn']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        burn_rt = rt_by_id[response['placement'][burn][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]

        # Move src & snk back to first and place burn on second
        #migrate(src_rt, rt1, src)
        migrate(burn_rt, rrt2, burn)
        #migrate(snk_rt, rt1, snk)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:burn'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        replicas = []
        fails = 0
        while len(replicas) < nbr_possible and fails < 100:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:burn'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.2)
        assert len(replicas) == nbr_possible
        print "REPLICAS", replicas
        placed_burn = {burn: rt2.id}
        print "ORIGINAL:", request_handler.get_actor(rt1, burn)
        for r in replicas:
            d = request_handler.get_actor(rt1, r)
            placed_burn[r] = d['node_id']
            print "REPLICA:", d
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        time.sleep(0.4)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        keys = set([k.keys()[0] for k in actual])
        print keys
        print [k.values()[0] for k in actual]
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        print [k.values()[0] for k in actual]

        # Make them dereplicate
        print "DEREPLICATE"
        for aid, nid in placed_burn.items():
            try:
                request_handler.report(rt_by_id[nid], aid, kwargs={'duration':0.01})
            except:
                print "FAILED DURATION CHANGE", aid
        fails = 0
        # This takes forever ..., but dereplication is slow
        monotonic_decrease = len(replicas)
        while len(replicas) > 0 and fails < nbr_possible * 30 + 60:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:burn'], root_prefix_level=3)['result']
            fails += 1
            assert monotonic_decrease >= len(replicas)
            monotonic_decrease = len(replicas)
            # Fail early if no progress
            if fails > 100:
                assert len(replicas) <= nbr_possible - 2
            elif fails > 70:
                assert len(replicas) <= nbr_possible - 1
            time.sleep(1)
        assert len(replicas) == 0
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:burn'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert burn not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left

    def testPerformanceSteadyReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.01)
            burn   : std.Burn(duration=0.005)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > burn.token
            burn.token > snk.token
            rule single: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            rule scale: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & performance_scaling(alone=true, max=6)
            apply burn: scale
            apply src, snk: single
        """

        global rt1, rt2, rt3

        nbr_possible = NBR_RUNTIMES - 2
        #rt1 = rt_order3[0]
        #rrt2 = rt_order3[1]
        #rt3 = rt_order3[2]
        rrt2 = rt2
        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response

        src = response['actor_map']['testScript:src']
        burn = response['actor_map']['testScript:burn']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        burn_rt = rt_by_id[response['placement'][burn][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]

        # Place burn on second
        migrate(burn_rt, rrt2, burn)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:burn'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        nbr_replicas = {}
        durations = [0.005, 0.015, 0.025, 0.035]
        for duration in durations[:nbr_possible + 1]:
            placed_burn = {burn: rt2.id}
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:burn'], root_prefix_level=3)['result']
            for r in replicas:
                d = request_handler.get_actor(rt1, r)
                placed_burn[r] = d['node_id']
            for aid, nid in placed_burn.items():
                try:
                    request_handler.report(rt_by_id[nid], aid, kwargs={'duration':duration})
                except:
                    print "FAILED DURATION CHANGE", aid
            duration_str = str(duration)
            for i in range(40):
                replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:burn'], root_prefix_level=3)['result']
                nbr_replicas.setdefault(duration_str, []).append(replicas)
                time.sleep(1)
            print "NBR REPLICAS", duration_str, ":", map(len, nbr_replicas[duration_str])

        def mean(array):
            a = map(len, array)
            return sum(a)/float(len(a))

        assert mean(nbr_replicas[str(0.005)]) < 0.2
        assert mean(nbr_replicas[str(0.015)]) > 0.5 and mean(nbr_replicas[str(0.015)]) < 1.9
        if nbr_possible > 1:
            assert mean(nbr_replicas[str(0.025)]) > 1.5 and mean(nbr_replicas[str(0.025)]) < 2.9
        if nbr_possible > 2:
            assert mean(nbr_replicas[str(0.035)]) > 2.5 and mean(nbr_replicas[str(0.035)]) < 3.9
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:burn'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert burn not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left

    def testManualConcurrentReplication(self, rt_order3):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            sum   : std.Sum()
            ident : std.Identity()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            ident.token[in](routing="collect-tagged")
            ident.token[out](routing="random")
            src.integer > sum.integer
            sum.integer > ident.token
            ident.token > snk.token
            rule manual: manual_scaling()
            apply sum, ident: manual
        """
        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response

        src = response['actor_map']['testScript:src']
        asum = response['actor_map']['testScript:sum']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        asum_rt = rt_by_id[response['placement'][asum][0]]
        ident_rt = rt_by_id[response['placement'][ident][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]

        # Move src & snk back to first and place sum on second
        migrate(src_rt, rt1, src)
        migrate(asum_rt, rt2, asum)
        migrate(ident_rt, rt2, ident)
        migrate(snk_rt, rt1, snk)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:sum'])['result']
        print replication_data
        sum_leader_id = replication_data['leader_node_id']
        sum_leader_rt = rt_by_id[sum_leader_id]

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:ident'])['result']
        print replication_data
        ident_leader_id = replication_data['leader_node_id']
        ident_leader_rt = rt_by_id[ident_leader_id]

        sum_counter = 0
        ident_counter = 0
        fails = 0
        while (sum_counter < 4 or ident_counter < 4) and fails < 20:
            failed = False
            if sum_counter < 4:
                sum_result = request_handler.async_replicate(sum_leader_rt, replication_id=response['replication_map']['testScript:sum'], dst_id=rt3.id)
            if ident_counter < 4:
                ident_result = request_handler.async_replicate(ident_leader_rt, replication_id=response['replication_map']['testScript:ident'], dst_id=rt3.id)
            if sum_counter < 4:
                try:
                    request_handler.async_response(sum_result)
                    sum_counter += 1
                    fails = 0
                except:
                    failed = True
            if ident_counter < 4:
                try:
                    request_handler.async_response(ident_result)
                    ident_counter += 1
                    fails = 0
                except:
                    failed = True
            if failed:
                fails += 1
                time.sleep(0.1)
        print "REPLICATED", sum_counter, ident_counter, fails
        assert sum_counter == 4 and ident_counter == 4
        sum_replicas = []
        fails = 0
        while len(sum_replicas) < sum_counter and fails < 20:
            sum_replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.1)
        assert len(sum_replicas) == sum_counter
        ident_replicas = []
        fails = 0
        while len(ident_replicas) < ident_counter and fails < 20:
            ident_replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.1)
        assert len(ident_replicas) == ident_counter
        print "REPLICAS SUM:", sum_replicas
        print "REPLICAS ident:", ident_replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, asum)
        for r in sum_replicas + ident_replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        tagtag = []
        fails = 0
        # Should get 25 combinations of port tags, i.e. paths thru scaled actors, otherwise not fully connected
        while len(tagtag) < 25 and fails < 10:
            time.sleep(0.5)
            actual = request_handler.report(runtimes[snk_place], snk)
            tagtag = set([k.keys()[0] + "+" + k.values()[0].keys()[0] for k in actual])
            fails += 1
        print "TAG-TAG combinations", len(tagtag), tagtag
        assert len(tagtag) == 25
        #keys = set([k.keys()[0] for k in actual])
        #print keys
        #print [k.values()[0] for k in actual]
        
        sum_replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
        ident_replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
        replicas = sum_replicas + ident_replicas
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert asum not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left

    def testDeviceTerminationReplication(self, rt_order3):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            sum   : std.Sum()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > sum.integer
            sum.integer > snk.token
            rule device: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & device_scaling(max=6)
            apply sum: device
        """
        global rt2
        from requests.exceptions import ConnectionError
        nbr_possible = NBR_RUNTIMES - (2 if rt2 == rt_order3[1] else 1) + 1
        rt1 = rt_order3[0]
        rrt2 = rt_order3[1]
        rt3 = rt_order3[2]
        rt_by_id = {r.id: r for r in runtimes}

        try:
            import re
            first_ip_addr = re.match("http://([0-9\.]*):.*", rt1.control_uri).group(1)
        except:
            raise Exception("Failed to get ip address from %s" % rt1.control_uri)
        rt_extra = helpers.setup_extra_local(first_ip_addr, request_handler, NBR_RUNTIMES + 1, proxy_storage=True)
        rt_by_id[rt_extra.id] = rt_extra

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response

        src = response['actor_map']['testScript:src']
        asum = response['actor_map']['testScript:sum']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        asum_rt = rt_by_id[response['placement'][asum][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]

        # Move src & snk back to first and place sum on second
        migrate(src_rt, rt1, src)
        migrate(asum_rt, rrt2, asum)
        migrate(snk_rt, rt1, snk)

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:sum'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        replicas = []
        fails = 0
        while len(replicas) < nbr_possible and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.2)
        assert len(replicas) == nbr_possible
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, asum)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        time.sleep(0.4)
        actual = sorted(request_handler.report(runtimes[snk_place], snk))
        #keys = set([k.keys()[0] for k in actual])
        #print keys
        #print [k.values()[0] for k in actual]
        #actual = sorted(request_handler.report(runtimes[snk_place], snk))
        #print [k.values()[0] for k in actual]
        request_handler.quit(rt_extra, method="migrate")
        replicas = []
        fails = 0
        while len(replicas) != (nbr_possible - 1) and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.2)
        assert len(replicas) == (nbr_possible - 1)
        # Make sure extra runtime is gone
        fails = 0
        while fails < 20:
            try:
                request_handler.get_node_id(rt_extra)
                # Should fail otherwise need to retry
                fails += 1
                time.sleep(0.2)
            except ConnectionError:
                _log.exception("expected ConnectionError exception for extra runtime")
                # Can't connect, i.e. gone
                break
            except Exception as e:
                _log.exception("expected exception for extra runtime")
                msg = str(e.message)
                if msg.startswith("504"):
                    # Timeout error, i.e. gone
                    break
                else:
                    # While quiting runtime send 500 errors, continue trying
                    fails += 1
                    time.sleep(0.2)
        assert fails != 20
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:sum'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        helpers.delete_app(request_handler, rt1, response['application_id'])
        actors_left = []
        for r in runtimes:
            actors_left.extend(request_handler.get_actors(r))
        print actors_left
        assert src not in actors_left
        assert asum not in actors_left
        assert snk not in actors_left
        for r in replicas:
            assert r not in actors_left


#@pytest.mark.skipif(calvinconfig.get().get("testing","proxy_storage") != 1, reason="Will likely fail with DHT")
@pytest.mark.slow
@pytest.mark.skip("For previous replication implementation")
class TestReplication(CalvinTestBase):

    def testSimpleReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            sum   : std.Sum()
            snk   : test.Sink(store_tokens=1, quiet=1)
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
            snk   : test.Sink(store_tokens=1, quiet=1)
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
            snk   : test.Sink(store_tokens=1, quiet=1)
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
            print "REPLICATING", asum, rts[i%2]
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
            snk   : test.Sink(store_tokens=1, quiet=1)
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
            snk   : test.Sink(store_tokens=1, quiet=1)
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
            src1    : test.FiniteCounter(start=0)
            src2    : test.FiniteCounter(start=10000)
            alt   : flow.Alternate2()
            snk   : test.Sink(store_tokens=1, quiet=1)
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
            src1    : test.FiniteCounter(start=0)
            src2    : test.FiniteCounter(start=10000, replicate_mult=true)
            alt   : flow.Alternate2()
            snk   : test.Sink(store_tokens=1, quiet=1)
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
        # Need to remove the last tokens since we have multiple paths and some tokens are likely still left on a path
        assert hh[:-10] == range(hh[0], hh[-10])
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
            src    : test.FiniteCounter(start=10000, replicate_mult=true)
            mid   : std.Identity()
            snk   : test.Sink(store_tokens=1, quiet=1)
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

    def testSimpleDereplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            sum   : std.Sum()
            snk   : test.Sink(store_tokens=1, quiet=1)
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
        deresult1a = request_handler.replicate(self.rt1, asum, self.rt2.id)
        deresult2a = request_handler.replicate(self.rt1, asum)
        time.sleep(0.5)
        deresult1b = request_handler.replicate(self.rt1, asum, dereplicate=True)
        deresult2b = request_handler.replicate(self.rt1, asum, dereplicate=True)
        print result, deresult1a, deresult1b, deresult2a, deresult2b
        time.sleep(0.5)
        asum_sum_first = request_handler.report(self.rt1, asum)
        actual_first = request_handler.report(self.rt1, snk)
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
        actors = request_handler.get_actors(self.rt1) + request_handler.get_actors(self.rt2)
        assert asum not in actors
        assert asum2 not in actors
        assert src not in actors
        assert snk not in actors
        assert deresult1a['actor_id'] not in actors
        assert deresult2a['actor_id'] not in actors

    def testSimpleExhaustDereplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            ident  : std.Identity()
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > ident.token
            ident.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        ident = d.actor_map['testScript:ident']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, ident)
        deresult1a = request_handler.replicate(self.rt1, ident)
        deresult2a = request_handler.replicate(self.rt1, ident)
        time.sleep(0.5)
        actual_first = request_handler.report(self.rt1, snk)
        ident_report2 = request_handler.report(self.rt1, deresult2a['actor_id'])
        deresult1b = request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True)
        ident_report1 = request_handler.report(self.rt1, deresult1a['actor_id'])
        deresult2b = request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True)
        print result, deresult1a, deresult1b, deresult2a, deresult2b
        print ident_report1, ident_report2
        time.sleep(0.5)
        actual_second = request_handler.report(self.rt1, snk)
        ident2 = result['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert ident2 in actors
        ident_meta = request_handler.get_actor(self.rt1, ident)
        ident2_meta = request_handler.get_actor(self.rt1, ident2)
        print ident_meta
        print ident2_meta
        for port in ident2_meta['inports']:
            r = request_handler.get_port(self.rt1, ident2, port['id'])
            print port['id'], ': ', r
        for port in ident2_meta['outports']:
            r = request_handler.get_port(self.rt1, ident2, port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        #print actual
        assert len(actual) > len(actual_first)
        assert len(actual_second) > len(actual_first)

        a = {}
        for t in actual_second:
            for k, v in t.items():
                a.setdefault(k,[]).append(v)
        print a

        assert not set.intersection(*[set(v) for v in a.values()])
        aa = []
        for v in a.values():
            aa.extend(v)
        s = sorted(aa)
        assert s == range(s[0], s[-1]+1)

        # This works since local is so fast, otherwise check how it is done in testSimpleRemoteReplication
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert ident2 not in actors
        assert src not in actors
        assert snk not in actors
        assert deresult1a['actor_id'] not in actors
        assert deresult2a['actor_id'] not in actors

    def testSlowExhaustDereplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            ident  : std.Identity()
            delay  : std.ClassicDelay(delay=0.1)
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        ident = d.actor_map['testScript:ident']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, ident)
        deresult1a = request_handler.replicate(self.rt1, ident)
        deresult2a = request_handler.replicate(self.rt1, ident)
        time.sleep(0.5)
        actual_first = request_handler.report(self.rt1, snk)
        ident_report2 = request_handler.report(self.rt1, deresult2a['actor_id'])
        deresult1b = request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True)
        ident_report1 = request_handler.report(self.rt1, deresult1a['actor_id'])
        deresult2b = request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True)
        print result, deresult1a, deresult1b, deresult2a, deresult2b
        print ident_report1, ident_report2
        time.sleep(0.2)
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(5)
        actual_second = request_handler.report(self.rt1, snk)
        ident2 = result['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert ident2 in actors
        ident_meta = request_handler.get_actor(self.rt1, ident)
        ident2_meta = request_handler.get_actor(self.rt1, ident2)
        print ident_meta
        print ident2_meta
        for port in ident2_meta['inports']:
            r = request_handler.get_port(self.rt1, ident2, port['id'])
            print port['id'], ': ', r
        for port in ident2_meta['outports']:
            r = request_handler.get_port(self.rt1, ident2, port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        #print actual
        assert len(actual) > len(actual_first)
        assert len(actual_second) > len(actual_first)

        a = {}
        for t in actual_second:
            for k, v in t.items():
                a.setdefault(k,[]).append(v)
        print a

        assert not set.intersection(*[set(v) for v in a.values()])
        aa = []
        for v in a.values():
            aa.extend(v)
        s = sorted(aa)
        assert s == range(s[0], s[-1]+1)

        # This works since local is so fast, otherwise check how it is done in testSimpleRemoteReplication
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert ident2 not in actors
        assert src not in actors
        assert snk not in actors
        assert deresult1a['actor_id'] not in actors
        assert deresult2a['actor_id'] not in actors

    def testManySlowExhaustDereplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            ident  : std.Identity()
            delay  : std.ClassicDelay(delay=0.1)
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        ident = d.actor_map['testScript:ident']
        snk = d.actor_map['testScript:snk']

        result_rep = []
        for i in range(10):
            print ">>>>>>replicate", i
            result_rep.append(request_handler.replicate(self.rt1, ident))
        result_derep = []
        for i in range(5):
            t = time.time()
            result_derep.append(request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True, timeout=10))
            print "dereplicate", i, time.time() - t, time.strftime("%H:%M:%S",time.localtime(t))
        for i in range(10):
            result_rep.append(request_handler.replicate(self.rt1, ident))
        for i in range(10):
            t = time.time()
            result_derep.append(request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True, timeout=10))
            print "dereplicate", i, time.time() - t, time.strftime("%H:%M:%S",time.localtime(t))
        time.sleep(0.5)
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(1)
        actual = request_handler.report(self.rt1, snk)
        actors = request_handler.get_actors(self.rt1)
        for r in result_rep[:5]:
            assert r['actor_id'] in actors
        for r in result_derep:
            assert r['actor_id'] not in actors
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert src not in actors
        assert snk not in actors
        for r in result_rep:
            assert r['actor_id'] not in actors

    def testSlowRemoteExhaustDereplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            ident  : std.Identity()
            delay  : std.ClassicDelay(delay=0.1)
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.3)

        src = d.actor_map['testScript:src']
        ident = d.actor_map['testScript:ident']
        snk = d.actor_map['testScript:snk']

        result = request_handler.replicate(self.rt1, ident)
        deresult1a = request_handler.replicate(self.rt1, ident, self.rt2.id)
        deresult2a = request_handler.replicate(self.rt1, ident, self.rt2.id)
        time.sleep(0.5)
        actual_first = request_handler.report(self.rt1, snk)
        ident_report2 = request_handler.report(self.rt2, deresult2a['actor_id'])
        deresult1b = request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True)
        ident_report1 = request_handler.report(self.rt2, deresult1a['actor_id'])
        deresult2b = request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True)
        print result, deresult1a, deresult1b, deresult2a, deresult2b
        print ident_report1, ident_report2
        time.sleep(0.2)
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(5)
        actual_second = request_handler.report(self.rt1, snk)
        ident2 = result['actor_id']
        actors = request_handler.get_actors(self.rt1)
        assert ident2 in actors
        ident_meta = request_handler.get_actor(self.rt1, ident)
        ident2_meta = request_handler.get_actor(self.rt1, ident2)
        print ident_meta
        print ident2_meta
        for port in ident2_meta['inports']:
            r = request_handler.get_port(self.rt1, ident2, port['id'])
            print port['id'], ': ', r
        for port in ident2_meta['outports']:
            r = request_handler.get_port(self.rt1, ident2, port['id'])
            print port['id'], ': ', r

        actual = request_handler.report(self.rt1, snk)
        #print actual
        assert len(actual) > len(actual_first)
        assert len(actual_second) > len(actual_first)

        a = {}
        for t in actual_second:
            for k, v in t.items():
                a.setdefault(k,[]).append(v)
        print a

        assert not set.intersection(*[set(v) for v in a.values()])
        aa = []
        for v in a.values():
            aa.extend(v)
        s = sorted(aa)
        assert s == range(s[0], s[-1]+1)

        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1) + request_handler.get_actors(self.rt2)
        assert ident not in actors
        assert ident2 not in actors
        assert src not in actors
        assert snk not in actors
        assert deresult1a['actor_id'] not in actors
        assert deresult2a['actor_id'] not in actors

    def testManySlowCollect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            i0     : std.Identity()
            i1     : std.Identity()
            i2     : std.Identity()
            i3     : std.Identity()
            i4     : std.Identity()
            i5     : std.Identity()
            i6     : std.Identity()
            i7     : std.Identity()
            i8     : std.Identity()
            i9     : std.Identity()
            i10     : std.Identity()
            i11     : std.Identity()
            i12     : std.Identity()
            i13     : std.Identity()
            i14     : std.Identity()
            i15     : std.Identity()
            i16     : std.Identity()
            i17     : std.Identity()
            i18     : std.Identity()
            i19     : std.Identity()
            delay  : std.ClassicDelay(delay=0.1)
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            delay.token[in](routing="collect-tagged")
            src.integer > i0.token
            src.integer > i1.token
            src.integer > i2.token
            src.integer > i3.token
            src.integer > i4.token
            src.integer > i5.token
            src.integer > i6.token
            src.integer > i7.token
            src.integer > i8.token
            src.integer > i9.token
            src.integer > i10.token
            src.integer > i11.token
            src.integer > i12.token
            src.integer > i13.token
            src.integer > i14.token
            src.integer > i15.token
            src.integer > i16.token
            src.integer > i17.token
            src.integer > i18.token
            src.integer > i19.token
            i0.token > delay.token
            i1.token > delay.token
            i2.token > delay.token
            i3.token > delay.token
            i4.token > delay.token
            i5.token > delay.token
            i6.token > delay.token
            i7.token > delay.token
            i8.token > delay.token
            i9.token > delay.token
            i10.token > delay.token
            i11.token > delay.token
            i12.token > delay.token
            i13.token > delay.token
            i14.token > delay.token
            i15.token > delay.token
            i16.token > delay.token
            i17.token > delay.token
            i18.token > delay.token
            i19.token > delay.token
            delay.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.2)
        src = d.actor_map['testScript:src']
        snk = d.actor_map['testScript:snk']
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(5)
        actual = []
        for i in range(20):
            print i
            a = request_handler.report(self.rt1, snk)
            if len(a) == len(actual):
                actual = a
                break
            actual = a
            time.sleep(1)
        a = {}
        for t in actual:
            for k, v in t.items():
                a.setdefault(k,[]).append(v)
        print a
        
    def testManyHeavyReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.022)
            ident  : std.Burn()
            delay  : std.Identity()
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="balanced")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()

        time.sleep(0.1)

        src = d.actor_map['testScript:src']
        ident = d.actor_map['testScript:ident']
        snk = d.actor_map['testScript:snk']

        request_handler.migrate(self.rt1, ident, self.rt2.id)

        ids = [r.id for r in runtimes][2:]
        result_rep = []
        for i in range(len(ids)):
            print ">>>>>>>>>>>>>>replicate", i
            result_rep.append(request_handler.replicate(self.rt2, ident, ids[i%len(ids)]))
        print "result_rep", result_rep
        result_derep = []
        #for i in range(5):
        #    t = time.time()
        #    result_derep.append(request_handler.replicate(self.rt1, ident, dereplicate=True, exhaust=True, timeout=10))
        #    print "dereplicate", i, time.time() - t, time.strftime("%H:%M:%S",time.localtime(t))
        time.sleep(15)
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(1)
        actual = request_handler.report(self.rt1, snk)
        actors = request_handler.get_actors(self.rt1)
        #for r in result_rep[:5]:
        #    assert r['actor_id'] in actors
        #for r in result_derep:
        #    assert r['actor_id'] not in actors
        helpers.destroy_app(d)
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert src not in actors
        assert snk not in actors
        #for r in result_rep:
        #    assert r['actor_id'] not in actors

    def testManyHeavyAutoReplication(self):
        _log.analyze("TESTRUN", "+", {})
        rt_map = {rt.id: rt for rt in self.runtimes}
        script = """
            src    : std.CountTimer(sleep=0.01)
            ident  : std.Burn()
            delay  : std.Identity()
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="balanced")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
            
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            rule rest: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}])
            apply src, snk, delay: first 
            apply ident: rest 
            
        """
        response = helpers.deploy_script(request_handler, "testScript", script, self.rt1)
        print response

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        time.sleep(0.1)

        # ident actor could be on any rest group runtime, need to know to ask it to auto-replicate
        for rt in self.runtimes:
            if ident in request_handler.get_actors(rt):
                break

        result_rep = request_handler.replicate(rt, ident, requirements={'op':"performance_scaling", 'kwargs':{'max': 6, 'alone': True}})
        print result_rep
        time.sleep(30)
        replicas = request_handler.get_index(self.rt1, "replicas/actors/"+result_rep['replication_id'], root_prefix_level=3)['result']
        assert len(replicas) >= (NBR_RUNTIMES - 2)
        print "------------ Burn less ----------------"
        actor_meta = request_handler.get_actor(self.rt1, ident)
        r = request_handler.report(rt_map[actor_meta["node_id"]], ident, kwargs={'duration': 0.001})
        replicas = request_handler.get_index(self.rt1, "replicas/actors/"+result_rep['replication_id'], root_prefix_level=3)['result']
        for replica in replicas:
            print "replica", replica
            try:
                actor_meta = request_handler.get_actor(self.rt1, replica)
                r = request_handler.report(rt_map[actor_meta["node_id"]], replica, kwargs={'duration': 0.001})
            except Exception as e:
                print e
        time.sleep(30)
        replicas2 = request_handler.get_index(self.rt1, "replicas/actors/"+result_rep['replication_id'], root_prefix_level=3)['result']
        assert len(replicas2) == 0
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(2)
        actual = request_handler.report(self.rt1, snk)
        actors = request_handler.get_actors(self.rt1)
        assert len(actual) == r
        for rt in self.runtimes:
            print rt.id, request_handler.get_actors(rt)
        helpers.delete_app(request_handler, self.rt1, response['application_id'])
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert src not in actors
        assert snk not in actors

    def testAutoDeviceReplication(self):
        _log.analyze("TESTRUN", "+", {})
        rt_map = {rt.id: rt for rt in self.runtimes}
        script = """
            src    : std.CountTimer(sleep=0.01)
            ident  : std.Burn(duration=0.01)
            delay  : std.Identity()
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="balanced")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
            
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            rule rest: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}])
            apply src, snk, delay: first 
            apply ident: rest 
            
        """
        response = helpers.deploy_script(request_handler, "testScript", script, self.rt1)
        print response

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        time.sleep(0.1)

        # ident actor could be on any rest group runtime, need to know to ask it to auto-replicate
        for rt in self.runtimes:
            if ident in request_handler.get_actors(rt):
                break

        result_rep = request_handler.replicate(rt, ident, requirements={'op':"device_scaling", 'kwargs':{}})
        print result_rep
        time.sleep(30)
        replicas = request_handler.get_index(self.rt1, "replicas/actors/"+result_rep['replication_id'], root_prefix_level=3)['result']
        print len(replicas), replicas
        assert len(replicas) >= (NBR_RUNTIMES - 2)
        
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(2)
        actual = request_handler.report(self.rt1, snk)
        actors = request_handler.get_actors(self.rt1)
        assert len(actual) == r
        for rt in self.runtimes:
            print rt.id, request_handler.get_actors(rt)
        helpers.delete_app(request_handler, self.rt1, response['application_id'])
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert src not in actors
        assert snk not in actors

    def testPerfRuleAutoReplication(self):
        _log.analyze("TESTRUN", "+", {})
        rt_map = {rt.id: rt for rt in self.runtimes}
        script = """
            src    : std.CountTimer(sleep=0.01)
            ident  : std.Burn()
            delay  : std.Identity()
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="balanced")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
            
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            rule rest: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & performance_scaling(max=6, alone=true)
            apply src, snk, delay: first 
            apply ident: rest 
            
        """
        response = helpers.deploy_script(request_handler, "testScript", script, self.rt1)
        print response

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        time.sleep(30)
        print "------------ Burn less ----------------"
        actor_meta = request_handler.get_actor(self.rt1, ident)
        print actor_meta
        r = request_handler.report(rt_map[actor_meta["node_id"]], ident, kwargs={'duration': 0.001})
        replicas = request_handler.get_index(self.rt1, "replicas/actors/"+actor_meta['replication_id'])['result']
        for replica in replicas:
            print "replica", replica
            try:
                actor_meta = request_handler.get_actor(self.rt1, replica)
                r = request_handler.report(rt_map[actor_meta["node_id"]], replica, kwargs={'duration': 0.001})
            except Exception as e:
                print e
        time.sleep(30)
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(2)
        actual = request_handler.report(self.rt1, snk)
        actors = request_handler.get_actors(self.rt1)
        for rt in self.runtimes:
            print rt.id, request_handler.get_actors(rt)
        helpers.delete_app(request_handler, self.rt1, response['application_id'])
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert src not in actors
        assert snk not in actors


    def testDeviceRuleAutoReplication(self):
        _log.analyze("TESTRUN", "+", {})
        rt_map = {rt.id: rt for rt in self.runtimes}
        script = """
            src    : std.CountTimer(sleep=0.01)
            ident  : std.Burn()
            delay  : std.Identity()
            snk    : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="balanced")
            delay.token[in](routing="collect-tagged")
            src.integer > ident.token
            ident.token > delay.token
            delay.token > snk.token
            
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            rule rest: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & device_scaling(max=6)
            apply src, snk, delay: first 
            apply ident: rest 
            
        """
        response = helpers.deploy_script(request_handler, "testScript", script, self.rt1)
        print response

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        time.sleep(0.1)

        time.sleep(30)
        # Stop the flood of tokens, to make sure all are passed
        r = request_handler.report(self.rt1, src, kwargs={'stopped': True})
        print "STOPPED Counter", r
        time.sleep(2)
        actual = request_handler.report(self.rt1, snk)
        actors = request_handler.get_actors(self.rt1)
        for rt in self.runtimes:
            print rt.id, request_handler.get_actors(rt)
        helpers.delete_app(request_handler, self.rt1, response['application_id'])
        time.sleep(1)
        actors = request_handler.get_actors(self.rt1)
        assert ident not in actors
        assert src not in actors
        assert snk not in actors

