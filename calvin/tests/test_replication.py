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


import time
import pytest
import os

from calvin.csparser import cscompile as compiler
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


#@pytest.fixture(params=[("rt1", "rt2", "rt3")])
#@pytest.fixture(params=[("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")
#,("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")
#,("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")
#])
@pytest.fixture(params=[("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")])
def rt_order3(request):
    return [globals()[p] for p in request.param]


@pytest.mark.slow
class TestReplication(object):
    def teardown_method(self, method):
        try:
            _log.debug("Test delete app when failed")
            if self.app_id is not None:
                helpers.delete_app(request_handler, rt1, self.app_id)
        except:
            _log.exception("Test delete app when failed")
        try:
            if self.rt_extra is not None:
                request_handler.quit(self.rt_extra, method="migrate")
        except:
            pass
        self.app_id = None


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
        self.app_id = response['application_id']

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
        self.app_id = None
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
            src   : test.FiniteCounter(start=100000, replicate_mult=true)
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
        self.app_id = response['application_id']

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
        # All min and max belongs in same 100000 range
        assert all([v[0]/100000 == v[1]/100000 for v in countersmm.values()])
        # All 5 10000 ranges included
        assert len(set([v[0]/100000 for v in countersmm.values()])) == 5
        print "MAX MIN", countersmm
        replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:src'], root_prefix_level=3)['result']
        print "REPLICAS", replicas
        self.app_id = None
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
        self.app_id = response['application_id']

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
        self.app_id = None
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
        self.app_id = response['application_id']

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
        self.app_id = None
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
        self.app_id = response['application_id']

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
        self.app_id = None
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
        self.app_id = response['application_id']

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
        self.app_id = None
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
        self.app_id = response['application_id']

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
        self.app_id = None
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
        self.app_id = response['application_id']

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
        self.app_id = None
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
        _log.debug("testManualConcurrentReplication %s" % map(str, rt_order3))
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
        self.app_id = response['application_id']

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
        while len(tagtag) < 25 and fails < 20:
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
        self.app_id = None
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
        self.rt_extra = rt_extra
        print "Extra runtime", rt_extra.id

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response
        self.app_id = response['application_id']

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
        self.rt_extra = None
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
                #_log.exception("expected ConnectionError exception for extra runtime")
                # Can't connect, i.e. gone
                break
            except Exception as e:
                #_log.exception("expected exception for extra runtime")
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
        self.app_id = None
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

    def testManualDereplicationExhaust(self, rt_order3):
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
            rule manual: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & manual_scaling()
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            apply ident: manual
            apply src, delay, snk: first
        """

        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response
        self.app_id = response['application_id']

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        delay = response['actor_map']['testScript:delay']
        snk = response['actor_map']['testScript:snk']

        actor_place = [request_handler.get_actors(r) for r in runtimes]
        src_rt = runtimes[map(lambda x: src in x, actor_place).index(True)]
        snk_rt = runtimes[map(lambda x: snk in x, actor_place).index(True)]
        ident_rt = runtimes[map(lambda x: ident in x, actor_place).index(True)]
        delay_rt = runtimes[map(lambda x: delay in x, actor_place).index(True)]

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:ident'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        # Replicate
        counter = 0
        fails = 0
        while counter < 2 and fails < 20:
            try:
                result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:ident'], dst_id=rt3.id)
                counter += 1
                fails = 0
            except:
                fails += 1
                time.sleep(0.2)
        print "REPLICATED", counter, fails
        assert counter == 2
        replicas = []
        fails = 0
        while len(replicas) < counter and fails < 40:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.1)
        assert len(replicas) == counter

        # Make sure we have at least 50 tokens and using all paths
        time.sleep(5)  # can't get more than one every 100 ms
        tokens1 = []
        fails = 0
        keys = set([])
        while len(tokens1) < 50 and len(keys) < (counter + 1) and fails < 20:
            tokens1 = request_handler.report(snk_rt, snk)
            keys = set([k.keys()[0] for k in tokens1])
            fails += 1
            time.sleep(0.5)
        assert len(tokens1) >= 50 and len(keys) == (counter + 1)

        # Dereplicate
        fails = 0
        while counter > 0 and fails < 20:
            try:
                result = request_handler.replicate(leader_rt, replication_id=response['replication_map']['testScript:ident'], dereplicate=True)
                counter -= 1
                fails = 0
            except:
                fails += 1
                time.sleep(0.2)
        print "DEREPLICATED", counter, fails
        assert counter == 0
        fails = 0
        while len(replicas) > 0 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.2)
        assert len(replicas) == 0

        # Stop the flood of tokens, to make sure all are passed
        src_counter = request_handler.report(src_rt, src, kwargs={'stopped': True})
        print "STOPPED Counter", src_counter

        # Make sure we have all tokens produced
        time.sleep((src_counter - len(tokens1)) * 0.1)  # wait at least for the new tokens
        tokens2 = []
        fails = 0
        while len(tokens2) < src_counter and fails < 20:
            tokens2 = request_handler.report(snk_rt, snk)
            fails += 1
            time.sleep(0.5)
        print tokens2
        assert len(tokens2) == src_counter

        self.app_id = None
        helpers.delete_app(request_handler, rt1, response['application_id'])

@pytest.mark.skipif(not os.getenv("CALVIN_CONSTRAINED", False),
    reason="Set env CALVIN_CONSTRAINED=<path>/calvin_c to run this test")
@pytest.mark.slow
class TestConstrainedReplication(object):
    def teardown_method(self, method):
        try:
            if self.constrained_proc:
                for cp in self.constrained_proc:
                    cp.terminate()
        except:
            pass
        self.constrained_proc = None
        try:
            if self.app_id is not None:
                helpers.delete_app(request_handler, rt1, self.app_id)
        except:
            pass
        self.app_id = None

    def testConstrainedDeviceReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            ident   : std.Identity()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > ident.token
            ident.token > snk.token
            rule manual: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & device_scaling()
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            apply ident: manual
            apply src, snk: first
        """

        #Start constrained
        try:
            import re
            first_ip_addr = re.match("http://([0-9\.]*):.*", rt1.control_uri).group(1)
            print "IP_ADDR", first_ip_addr
        except:
            raise Exception("Failed to get ip address from %s" % rt1.control_uri)
        try:
            # Remove state if exist
            os.remove("calvin.msgpack")
        except:
            pass
        from subprocess import Popen
        constrained_p = range(3)
        for i in range(3):
            constrained_p[i] = Popen([os.getenv("CALVIN_CONSTRAINED"), '-a',
            '{"indexed_public": {"node_name": {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest", "name": "constrained%d"}}}' % i,
            '-u', 'calvinip://%s:5200' % first_ip_addr])
        self.constrained_proc = constrained_p
        time.sleep(1)

        constrained_id = range(3)
        constrained_data = range(3)
        for i in range(3):
            fails = 0
            while fails < 20:
                try:
                    constrained_id[i] = request_handler.get_index(rt1, "/node/attribute/node_name/com.ericsson//distributed-test/rest/constrained%d"%i)['result'][0]
                    constrained_data[i] = request_handler.get_node(rt1, constrained_id[i])
                    break
                except:
                    fails += 1
                    time.sleep(0.1)
            print "CONSTRAINED DATA", constrained_data[i]

        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response
        self.app_id = response['application_id']

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]
        #ident_rt = rt_by_id[response['placement'][ident][0]]
        ident_rt_id = response['placement'][ident][0]

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:ident'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        # Make sure we have all the replicas
        replicas = []
        fails = 0
        while len(replicas) < 4 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.3)
        assert len(replicas) == 4
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, ident)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        # Make sure that all paths thru replicas are used
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        keys = []
        fails = 0
        while len(keys) < 5 and fails < 20:
            time.sleep(0.2)
            actual = request_handler.report(runtimes[snk_place], snk)
            keys = set([k.keys()[0] for k in actual])
            fails += 1
        print keys
        print sorted([k.values()[0] for k in actual])
        assert len(keys) == 5

        # abolish a constrained runtime not having the original actor
        c_id = constrained_id[:]
        try:
            c_id.remove(ident_rt_id)
            print "original actor on constrained"
        except:
            print "original actor not on constrained"
        request_handler.abolish_proxy_peer(rt_by_id[constrained_data[0]['proxy']], c_id[0])

        # Make sure that the replica is gone
        fails = 0
        while len(replicas) > 3 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.3)
        print replicas
        assert len(replicas) == 3

        self.app_id = None
        helpers.delete_app(request_handler, rt1, response['application_id'])

        # Now all replicas should be gone
        fails = 0
        while len(replicas) > 0 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.1)
        print replicas
        assert not replicas

        # Delete the remaining constrained runtimes
        cc_id = constrained_id[:]
        cc_id.remove(c_id[0])
        for i in cc_id:
            request_handler.abolish_proxy_peer(rt_by_id[constrained_data[0]['proxy']], i)

    def testConstrainedShadowDeviceReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            ident   : test.FakeShadow()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > ident.token
            ident.token > snk.token
            rule manual: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & device_scaling()
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            apply ident: manual
            apply src, snk: first
        """

        #Start constrained
        try:
            import re
            first_ip_addr = re.match("http://([0-9\.]*):.*", rt1.control_uri).group(1)
            print "IP_ADDR", first_ip_addr
        except:
            raise Exception("Failed to get ip address from %s" % rt1.control_uri)
        try:
            # Remove state if exist
            os.remove("calvin.msgpack")
        except:
            pass
        from subprocess import Popen
        constrained_p = range(3)
        for i in range(3):
            constrained_p[i] = Popen([os.getenv("CALVIN_CONSTRAINED"), '-a',
            '{"indexed_public": {"node_name": {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest", "name": "constrained%d"}}}' % i,
            '-u', 'calvinip://%s:5200' % first_ip_addr])
        self.constrained_proc = constrained_p
        time.sleep(1)

        constrained_id = range(3)
        constrained_data = range(3)
        for i in range(3):
            fails = 0
            while fails < 20:
                try:
                    constrained_id[i] = request_handler.get_index(rt1, "/node/attribute/node_name/com.ericsson//distributed-test/rest/constrained%d"%i)['result'][0]
                    constrained_data[i] = request_handler.get_node(rt1, constrained_id[i])
                    break
                except:
                    fails += 1
                    time.sleep(0.1)
            print "CONSTRAINED DATA", constrained_data[i]

        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response
        self.app_id = response['application_id']

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]
        #ident_rt = rt_by_id[response['placement'][ident][0]]
        ident_rt_id = response['placement'][ident][0]

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:ident'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        # Make sure we have all the replicas
        replicas = []
        fails = 0
        while len(replicas) < 4 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.3)
        assert len(replicas) == 4
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, ident)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        # Make sure that all paths thru replicas are used
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        keys = []
        fails = 0
        while len(keys) < 5 and fails < 20:
            time.sleep(0.2)
            actual = request_handler.report(runtimes[snk_place], snk)
            keys = set([k.keys()[0] for k in actual])
            fails += 1
        print keys
        print sorted([k.values()[0] for k in actual])
        assert len(keys) == 5

        # abolish a constrained runtime not having the original actor
        c_id = constrained_id[:]
        try:
            c_id.remove(ident_rt_id)
            print "original actor on constrained"
        except:
            print "original actor not on constrained"
        request_handler.abolish_proxy_peer(rt_by_id[constrained_data[0]['proxy']], c_id[0])

        # Make sure that the replica is gone
        fails = 0
        while len(replicas) > 3 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.3)
        print replicas
        assert len(replicas) == 3

        self.app_id = None
        helpers.delete_app(request_handler, rt1, response['application_id'])

        # Now all replicas should be gone
        fails = 0
        while len(replicas) > 0 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.1)
        print replicas
        assert not replicas

        # Delete the remaining constrained runtimes
        cc_id = constrained_id[:]
        cc_id.remove(c_id[0])
        for i in cc_id:
            request_handler.abolish_proxy_peer(rt_by_id[constrained_data[0]['proxy']], i)

    def testConstrainedDidReplication(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.CountTimer(sleep=0.03)
            ident   : test.ReplicaIdentity()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-tagged")
            src.integer > ident.token
            ident.token > snk.token
            rule manual: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest"}]) & device_scaling()
            rule first: node_attr_match(index=["node_name", {"organization": "com.ericsson", "purpose": "distributed-test", "group": "first"}])
            apply ident: manual
            apply src, snk: first
        """

        #Start constrained
        try:
            import re
            first_ip_addr = re.match("http://([0-9\.]*):.*", rt1.control_uri).group(1)
            print "IP_ADDR", first_ip_addr
        except:
            raise Exception("Failed to get ip address from %s" % rt1.control_uri)
        try:
            # Remove state if exist
            os.remove("calvin.msgpack")
        except:
            pass
        from subprocess import Popen
        constrained_p = range(3)
        for i in range(3):
            constrained_p[i] = Popen([os.getenv("CALVIN_CONSTRAINED"), '-a',
            '{"indexed_public": {"node_name": {"organization": "com.ericsson", "purpose": "distributed-test", "group": "rest", "name": "constrained%d"}}}' % i,
            '-u', 'calvinip://%s:5200' % first_ip_addr])
        self.constrained_proc = constrained_p
        time.sleep(1)

        constrained_id = range(3)
        constrained_data = range(3)
        for i in range(3):
            fails = 0
            while fails < 20:
                try:
                    constrained_id[i] = request_handler.get_index(rt1, "/node/attribute/node_name/com.ericsson//distributed-test/rest/constrained%d"%i)['result'][0]
                    constrained_data[i] = request_handler.get_node(rt1, constrained_id[i])
                    break
                except:
                    fails += 1
                    time.sleep(0.1)
            print "CONSTRAINED DATA", constrained_data[i]

        rt_by_id = {r.id: r for r in runtimes}

        response = helpers.deploy_script(request_handler, "testScript", script, rt1)
        print response
        self.app_id = response['application_id']

        src = response['actor_map']['testScript:src']
        ident = response['actor_map']['testScript:ident']
        snk = response['actor_map']['testScript:snk']

        # Assuming the migration was successful for the first possible placement
        src_rt = rt_by_id[response['placement'][src][0]]
        snk_rt = rt_by_id[response['placement'][snk][0]]
        #ident_rt = rt_by_id[response['placement'][ident][0]]
        ident_rt_id = response['placement'][ident][0]

        time.sleep(0.3)

        replication_data = request_handler.get_storage(rt1, key="replicationdata-" + response['replication_map']['testScript:ident'])['result']
        print replication_data
        leader_id = replication_data['leader_node_id']
        leader_rt = rt_by_id[leader_id]

        # Make sure we have all the replicas
        replicas = []
        fails = 0
        while len(replicas) < 4 and fails < 20:
            replicas = request_handler.get_index(rt1, "replicas/actors/"+response['replication_map']['testScript:ident'], root_prefix_level=3)['result']
            fails += 1
            time.sleep(0.3)
        assert len(replicas) == 4
        print "REPLICAS", replicas
        print "ORIGINAL:", request_handler.get_actor(rt1, ident)
        for r in replicas:
            print "REPLICA:", request_handler.get_actor(rt1, r)
        # Make sure that all paths thru replicas are used
        actor_place = [request_handler.get_actors(r) for r in runtimes]
        snk_place = map(lambda x: snk in x, actor_place).index(True)
        keys = []
        fails = 0
        while len(keys) < 5 and fails < 20:
            time.sleep(0.2)
            actual = request_handler.report(runtimes[snk_place], snk)
            keys = set([k.keys()[0] for k in actual])
            fails += 1
        print keys
        assert len(keys) == 5

        tag_index = set([k.keys()[0] + ":" + k.values()[0].split(':', 1)[0] for k in actual])
        print tag_index
        assert len(tag_index) == 5

        self.app_id = None
        helpers.delete_app(request_handler, rt1, response['application_id'])

        # Delete the constrained runtimes
        for i in constrained_id:
            request_handler.abolish_proxy_peer(rt_by_id[constrained_data[0]['proxy']], i)
