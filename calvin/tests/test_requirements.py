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
import copy
import multiprocessing
from calvin.runtime.north import calvin_node
from calvin.Tools import cscompiler as compiler
from calvin.Tools import deployer
import pytest
from calvin.utilities import utils
from calvin.utilities.nodecontrol import dispatch_node, dispatch_storage_node
from calvin.utilities import calvinuuid
from warnings import warn
from calvin.utilities.attribute_resolver import format_index_string
import socket
import os
import json
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

try:
    ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
except:
    import socket
    ip_addr = socket.gethostbyname(socket.gethostname())

rt1 = None
rt2 = None
rt3 = None
rt1_id = None
rt2_id = None
rt3_id = None
test_script_dir = None

def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


@pytest.mark.slow
class TestDeployScript(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        global rt1
        global rt2
        global rt3
        global test_script_dir
        rt1, _ = dispatch_node(["calvinip://%s:5000" % (ip_addr,)], "http://%s:5003" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})
        time.sleep(1)  # Less storage operations are droped if we wait a bit
        rt2, _ = dispatch_node(["calvinip://%s:5001" % (ip_addr,)], "http://%s:5004" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})
        time.sleep(1)  # Less storage operations are droped if we wait a bit
        rt3, _ = dispatch_node(["calvinip://%s:5002" % (ip_addr,)], "http://%s:5005" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner2'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode3'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 2}}})
        time.sleep(1)  # Less storage operations are droped if we wait a bit

        test_script_dir = absolute_filename('scripts/')
        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt1
        global rt2
        global rt3
        utils.quit(rt1)
        utils.quit(rt2)
        utils.quit(rt3)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        time.sleep(0.2)

    def verify_storage(self):
        global rt1
        global rt2
        global rt3
        rt1_id = None
        rt2_id = None
        rt3_id = None
        failed = True
        # Try 10 times waiting for control API to be up and running
        for i in range(10):
            try:
                rt1_id = rt1_id or utils.get_node_id(rt1)
                rt2_id = rt2_id or utils.get_node_id(rt2)
                rt3_id = rt3_id or utils.get_node_id(rt3)
                failed = False
                break
            except:
                time.sleep(0.1)
        assert not failed
        assert rt1_id
        assert rt2_id
        assert rt3_id
        print "RUNTIMES:", rt1_id, rt2_id, rt3_id
        _log.analyze("TESTRUN", "+ IDS", {'waited': 0.1*i})
        failed = True
        # Try 20 times waiting for storage to be connected
        caps1 = []
        caps2 = []
        caps3 = []
        rt_ids = set([rt1_id, rt2_id, rt3_id])
        for i in range(20):
            try:
                if not (rt1_id in caps1  and rt2_id in caps2 and rt3_id in caps1):
                    caps1 = utils.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps2 and rt2_id in caps2 and rt3_id in caps2):
                    caps2 = utils.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps3 and rt2_id in caps3 and rt3_id in caps3):
                    caps3 = utils.get_index(rt3, "node/capabilities/calvinsys.native.python-json")['result']
                if rt_ids <= set(caps1) and rt_ids <= set(caps2) and rt_ids <= set(caps3):
                    failed = False
                    break
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        assert not failed
        _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})
        assert utils.get_index(rt2, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
        assert utils.get_index(rt3, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
        assert utils.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        assert utils.get_index(rt3, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        assert utils.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode3'}]))
        assert utils.get_index(rt2, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode3'}]))
        assert utils.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        _log.analyze("TESTRUN", "+ RT INDEX", {})

    @pytest.mark.slow
    def testDeploySimple(self):
        _log.analyze("TESTRUN", "+", {})
        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_deploy1.calvin"), attr=None,
                                reqs=test_script_dir+"test_deploy1.deployjson", check=True)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        time.sleep(2)
        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt2, sum -> rt2, snk -> rt3
        assert result['actor_map']['test_deploy1:src'] in actors[1]
        assert result['actor_map']['test_deploy1:sum'] in actors[1]
        assert result['actor_map']['test_deploy1:snk'] in actors[2]
        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeployLongActorChain(self):
        _log.analyze("TESTRUN", "+", {})
        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_deploy2.calvin"), attr=None,
                                reqs=test_script_dir+"test_deploy2.deployjson", check=True)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        time.sleep(2)
        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt1, sum[1:8] -> [rt1, rt2, rt3], snk -> rt3
        assert result['actor_map']['test_deploy2:src'] in actors[0]
        assert result['actor_map']['test_deploy2:snk'] in actors[2]
        sum_list=[result['actor_map']['test_deploy2:sum%d'%i] for i in range(1,9)]
        sum_place = [0 if a in actors[0] else 1 if a in actors[1] else 2 if a in actors[2] else -1 for a in sum_list]
        assert not any([p==-1 for p in sum_place])
        assert all(x<=y for x, y in zip(sum_place, sum_place[1:]))
        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeployComponent(self):
        _log.analyze("TESTRUN", "+", {})
        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_deploy3.calvin"), attr=None,
                                reqs=test_script_dir+"test_deploy3.deployjson", check=True)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        time.sleep(2)
        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src:(first, second) -> rt1, sum -> rt2, snk -> rt3
        assert result['actor_map']['test_deploy3:src:first'] in actors[0]
        assert result['actor_map']['test_deploy3:src:second'] in actors[0]
        assert result['actor_map']['test_deploy3:sum'] in actors[1]
        assert result['actor_map']['test_deploy3:snk'] in actors[2]
        utils.delete_application(rt1, result['application_id'])

rt1 = None
rt2 = None
test_script_dir = None

@pytest.mark.slow
class TestDeployShadow(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        global rt1
        global rt2
        global test_script_dir
        rt1, _ = dispatch_node(["calvinip://%s:5000" % (ip_addr,)], "http://%s:5003" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})

        # Hack to get different config actorpath in actor store for each runtime and blacklist timers on node2
        # (since dispatch will use the same global)
        # FIXME do it properly
        import calvin.actorstore.store
        import calvin.calvinsys
        import copy
        calvin.actorstore.store._conf = copy.deepcopy(calvin.actorstore.store._conf)
        calvin.actorstore.store._conf.config['global']['actor_paths'] = [absolute_filename('test_store')]
        calvin.calvinsys._conf = copy.deepcopy(calvin.actorstore.store._conf)
        calvin.calvinsys._conf.config['global']['capabilities_blacklist'] = ['calvinsys.events.timer']
        time.sleep(1)  # Less storage operations are droped if we wait a bit
        rt2, _ = dispatch_node(["calvinip://%s:5001" % (ip_addr,)], "http://%s:5004" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})
        time.sleep(1)  # Less storage operations are droped if we wait a bit

        test_script_dir = absolute_filename('scripts/')
        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt1
        global rt2
        utils.quit(rt1)
        utils.quit(rt2)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        time.sleep(0.2)

    def verify_storage(self):
        global rt1
        global rt2
        rt1_id = None
        rt2_id = None
        failed = True
        # Try 10 times waiting for control API to be up and running
        for i in range(10):
            try:
                rt1_id = rt1_id or utils.get_node_id(rt1)
                rt2_id = rt2_id or utils.get_node_id(rt2)
                failed = False
                break
            except:
                time.sleep(0.1)
        assert not failed
        assert rt1_id
        assert rt2_id
        print "RUNTIMES:", rt1_id, rt2_id
        _log.analyze("TESTRUN", "+ IDS", {'waited': 0.1*i})
        failed = True
        # Try 20 times waiting for storage to be connected
        caps1 = []
        caps2 = []
        rt_ids = set([rt1_id, rt2_id])
        for i in range(20):
            try:
                if not (rt1_id in caps1 and rt2_id in caps1):
                    caps1 = utils.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps2 and rt2_id in caps2):
                    caps2 = utils.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if rt_ids <= set(caps1) and rt_ids <= set(caps2):
                    failed = False
                    break
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        assert not failed
        _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})
        # Now check for the values needed by this specific test
        caps = utils.get_index(rt1, 'node/capabilities/calvinsys.events.timer')
        assert rt1_id in caps['result']
        _log.analyze("TESTRUN", "+ RT1 CAPS", {})
        caps = utils.get_index(rt2, 'node/capabilities/calvinsys.events.timer')
        assert rt1_id in caps['result']
        _log.analyze("TESTRUN", "+ RT2 CAPS", {})
        assert utils.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        _log.analyze("TESTRUN", "+ RT1 INDEX", {})
        assert utils.get_index(rt2, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
        _log.analyze("TESTRUN", "+ RT2 INDEX", {})

    @pytest.mark.slow
    def testDeployShadow(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow1.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow1.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[0]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]

        actual = utils.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) > 5
        assert all([y-x > 0 for x, y in zip(actual, actual[1:])])
        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeployRequiresShadow(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow1.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow2.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[0]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]

        actual = utils.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) > 5
        assert all([y-x > 0 for x, y in zip(actual, actual[1:])])
        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeployRequiresCapabilityShadow(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow3.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow2.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow3:src'] in actors[0]
        assert result['actor_map']['test_shadow3:sum'] in actors[1]
        assert result['actor_map']['test_shadow3:snk'] in actors[0]

        actual = utils.report(rt1, result['actor_map']['test_shadow3:snk'])
        assert len(actual) > 5
        assert all([y-x > 0 for x, y in zip(actual, actual[1:])])
        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeployShadowComponent(self):
        _log.analyze("TESTRUN", "+", {})
        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadowcomponent1.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadowcomponent1.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        time.sleep(2)
        actors = [utils.get_actors(rt1), utils.get_actors(rt2)]
        # src:(first, second) -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadowcomponent1:src:first'] in actors[1]
        assert result['actor_map']['test_shadowcomponent1:src:second'] in actors[1]
        assert result['actor_map']['test_shadowcomponent1:sum'] in actors[0]
        assert result['actor_map']['test_shadowcomponent1:snk'] in actors[0]
        utils.delete_application(rt1, result['application_id'])


@pytest.mark.slow
class TestSepDeployShadow(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        global rt1
        global rt2
        global rt3
        global test_script_dir
        rt1_conf = copy.deepcopy(_conf)
        rt1_conf.save("/tmp/calvin5000.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5000"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5000, controlport=5003, attr={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5000.conf")
        rt1 = utils.RT("http://%s:5003" % ip_addr)
        rt2_conf = copy.deepcopy(_conf)
        rt2_conf.set('global', 'actor_paths', [absolute_filename('test_store')])
        rt2_conf.set('global', 'capabilities_blacklist', ['calvinsys.events.timer'])
        rt2_conf.save("/tmp/calvin5001.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5001"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5001, controlport=5004, attr={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5001.conf")
        rt2 = utils.RT("http://%s:5004" % ip_addr)
        rt3_conf = copy.deepcopy(_conf)
        rt3_conf.set('global', 'actor_paths', [absolute_filename('test_store')])
        rt3_conf.set('global', 'capabilities_blacklist', ['calvinsys.events.timer'])
        rt3_conf.save("/tmp/calvin5002.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5002"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5002, controlport=5005, attr={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode3'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5002.conf")
        rt3 = utils.RT("http://%s:5005" % ip_addr)

        test_script_dir = absolute_filename('scripts/')
        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt1
        global rt2
        global rt3
        utils.quit(rt1)
        utils.quit(rt2)
        utils.quit(rt3)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        os.system("pkill -9 -f -l 'csruntime -n %s -p 5000'" % (ip_addr,))
        os.system("pkill -9 -f -l 'csruntime -n %s -p 5001'" % (ip_addr,))
        os.system("pkill -9 -f -l 'csruntime -n %s -p 5002'" % (ip_addr,))
        time.sleep(0.2)

    def verify_storage(self):
        global rt1
        global rt2
        global rt3
        global rt1_id
        global rt2_id
        global rt3_id
        rt1_id = None
        rt2_id = None
        rt3_id = None
        failed = True
        # Try 10 times waiting for control API to be up and running
        for i in range(10):
            try:
                rt1_id = rt1_id or utils.get_node_id(rt1)
                rt2_id = rt2_id or utils.get_node_id(rt2)
                rt3_id = rt3_id or utils.get_node_id(rt3)
                failed = False
                break
            except:
                time.sleep(0.1)
        assert not failed
        assert rt1_id
        assert rt2_id
        assert rt3_id
        print "RUNTIMES:", rt1_id, rt2_id, rt3_id
        _log.analyze("TESTRUN", "+ IDS", {'waited': 0.1*i})
        failed = True
        # Try 20 times waiting for storage to be connected
        caps1 = []
        caps2 = []
        caps3 = []
        rt_ids = set([rt1_id, rt2_id, rt3_id])
        for i in range(20):
            try:
                if not (rt1_id in caps1 and rt2_id in caps1 and rt3_id in caps1):
                    caps1 = utils.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps2 and rt2_id in caps2 and rt3_id in caps2):
                    caps2 = utils.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps3 and rt2_id in caps3 and rt3_id in caps3):
                    caps3 = utils.get_index(rt3, "node/capabilities/calvinsys.native.python-json")['result']
                if rt_ids <= set(caps1) and rt_ids <= set(caps2) and rt_ids <= set(caps3):
                    failed = False
                    break
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        assert not failed
        _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})
        # Now check for the values needed by this specific test
        caps = utils.get_index(rt1, 'node/capabilities/calvinsys.events.timer')
        assert rt1_id in caps['result']
        _log.analyze("TESTRUN", "+ RT1 CAPS", {})
        caps = utils.get_index(rt2, 'node/capabilities/calvinsys.events.timer')
        assert rt1_id in caps['result']
        _log.analyze("TESTRUN", "+ RT2 CAPS", {})
        assert utils.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        _log.analyze("TESTRUN", "+ RT1 INDEX", {})
        assert utils.get_index(rt2, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
        _log.analyze("TESTRUN", "+ RT2 INDEX", {})

    @pytest.mark.slow
    def testSepDeployShadow(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow1.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow1.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        assert result['requirements_fulfilled']
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[0]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]

        actual = utils.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) > 5
        assert all([y-x > 0 for x, y in zip(actual, actual[1:])])

        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeployStillShadow(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global rt3
        global rt1_id
        global rt2_id
        global rt3_id
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5004' % ip_addr,
                          script=open(test_script_dir+"test_shadow1.calvin"), attr=None,
                                reqs=None, check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        assert result['requirements_fulfilled']
        time.sleep(1)
        utils.migrate(rt2, result['actor_map']['test_shadow1:snk'], rt1_id)
        time.sleep(1)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt2, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[1]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]

        actual = utils.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) == 0
        utils.migrate(rt2, result['actor_map']['test_shadow1:src'], rt3_id)
        time.sleep(1)
        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt3, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[2]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]
        actual = utils.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) == 0
        utils.migrate(rt3, result['actor_map']['test_shadow1:src'], rt1_id)
        time.sleep(1)
        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[0]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]
        actual = utils.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) > 3

        utils.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testDeployFailReqs(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global rt3
        global rt1_id
        global rt2_id
        global rt3_id
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5004' % ip_addr,
                          script=open(test_script_dir+"test_shadow1.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow6.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(1)
        assert not result['requirements_fulfilled']
        utils.delete_application(rt2, result['application_id'])

@pytest.mark.slow
class TestDeployment3NodesProxyStorage(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        global rt1
        global rt2
        global rt3
        global test_script_dir
        use_proxy_storage = True

        rt1_conf = copy.deepcopy(_conf)
        rt1_conf.set('global', 'capabilities_blacklist', ['calvinsys.events.timer'])
        if use_proxy_storage:
            rt1_conf.set('global', 'storage_start', False)
        rt1_conf.save("/tmp/calvin5000.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5000"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5000, controlport=5003, attr={'indexed_public':
                  {'node_name': {'name': 'display'}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5000.conf")
        rt1 = utils.RT("http://%s:5003" % ip_addr)
        time.sleep(1)

        rt2_3_conf = copy.deepcopy(_conf)
        if use_proxy_storage:
            rt2_3_conf.set('global', 'storage_proxy', "calvinip://%s:5000" % ip_addr)
        rt2_3_conf.save("/tmp/calvin5001.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5001"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5001, controlport=5004, attr={'indexed_public':
                  {'node_name': {'name': 'serv'},
                   'address': {"locality" : "outside"}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5001.conf")
        rt2 = utils.RT("http://%s:5004" % ip_addr)

        rt2_3_conf.save("/tmp/calvin5002.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5002"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5002, controlport=5005, attr={'indexed_public':
                  {'node_name': {'name': 'mtrx'},
                   'address': {"locality" : "inside"}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5002.conf")
        rt3 = utils.RT("http://%s:5005" % ip_addr)

        test_script_dir = absolute_filename('scripts/')
        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt1
        global rt2
        global rt3
        utils.quit(rt1)
        utils.quit(rt2)
        utils.quit(rt3)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        os.system("pkill -9 -f 'csruntime -n %s -p 5000'" % (ip_addr,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5001'" % (ip_addr,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5002'" % (ip_addr,))
        time.sleep(0.2)

    def verify_storage(self):
        global rt1
        global rt2
        global rt3
        global rt1_id
        global rt2_id
        global rt3_id
        rt1_id = None
        rt2_id = None
        rt3_id = None
        failed = True
        # Try 10 times waiting for control API to be up and running
        for i in range(10):
            try:
                rt1_id = rt1_id or utils.get_node_id(rt1)
                rt2_id = rt2_id or utils.get_node_id(rt2)
                rt3_id = rt3_id or utils.get_node_id(rt3)
                failed = False
                break
            except:
                time.sleep(0.1)
        assert not failed
        assert rt1_id
        assert rt2_id
        assert rt3_id
        print "RUNTIMES:", rt1_id, rt2_id, rt3_id
        _log.analyze("TESTRUN", "+ IDS", {'waited': 0.1*i})
        failed = True
        # Try 20 times waiting for storage to be connected
        caps1 = []
        caps2 = []
        caps3 = []
        rt_ids = set([rt1_id, rt2_id, rt3_id])
        for i in range(20):
            try:
                if not (rt1_id in caps1 and rt2_id in caps1 and rt3_id in caps1):
                    caps1 = utils.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps2 and rt2_id in caps2 and rt3_id in caps2):
                    caps2 = utils.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps3 and rt2_id in caps3 and rt3_id in caps3):
                    caps3 = utils.get_index(rt3, "node/capabilities/calvinsys.native.python-json")['result']
                if rt_ids <= set(caps1) and rt_ids <= set(caps2) and rt_ids <= set(caps3):
                    failed = False
                    break
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        assert not failed
        _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})

    @pytest.mark.slow
    def testDeploy3NodesProxyStorageShadow(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global rt3
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow4.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow4.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow4:button'] in actors[1]
        assert result['actor_map']['test_shadow4:check'] in actors[0]
        assert result['actor_map']['test_shadow4:bell'] in actors[2]

        actual = utils.report(rt3, result['actor_map']['test_shadow4:bell'])
        assert len(actual) > 5
        assert all([y-x > 0 for x, y in zip(actual, actual[1:])])

        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeploy3NodesProxyStorageMoveAgain(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global rt3
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow4.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow4.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow4:button'] in actors[1]
        assert result['actor_map']['test_shadow4:check'] in actors[0]
        assert result['actor_map']['test_shadow4:bell'] in actors[2]

        actual = utils.report(rt3, result['actor_map']['test_shadow4:bell'])
        assert len(actual) > 5
        utils.migrate_use_req(rt3, result['actor_map']['test_shadow4:bell'],
                                [{
                                    "op": "node_attr_match",
                                    "kwargs": {"index": ["address", {"locality": "outside"}]},
                                    "type": "+"
                                }])
        time.sleep(1)
        actors2 = utils.get_actors(rt2)
        assert result['actor_map']['test_shadow4:bell'] in actors2
        actual2 = utils.report(rt2, result['actor_map']['test_shadow4:bell'])
        assert len(actual2) > len(actual)
        assert all([y-x > 0 for x, y in zip(actual2, actual2[1:])])

        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeploy3NodesProxyStorageMoveAllAgain(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global rt3
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow4.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow4.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow4:button'] in actors[1]
        assert result['actor_map']['test_shadow4:check'] in actors[0]
        assert result['actor_map']['test_shadow4:bell'] in actors[2]

        actual = utils.report(rt3, result['actor_map']['test_shadow4:bell'])
        assert len(actual) > 5
        utils.migrate_app_use_req(rt3, result['application_id'],
                            {
                                "requirements": {
                                    "button": [
                                        {
                                          "op": "node_attr_match",
                                            "kwargs": {"index": ["address", {"locality": "inside"}]},
                                            "type": "+"
                                       }],
                                        "bell": [
                                        {
                                            "op": "node_attr_match",
                                            "kwargs": {"index": ["address", {"locality": "outside"}]},
                                            "type": "+"
                                        }],
                                        "check": [
                                        {
                                            "op": "node_attr_match",
                                            "kwargs": {"index": ["node_name", {"name": "display"}]},
                                            "type": "+"
                                        }]
                                }
                            })
        time.sleep(1)
        actors2 = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        assert result['actor_map']['test_shadow4:bell'] in actors2[1]
        assert result['actor_map']['test_shadow4:check'] in actors[0]
        assert result['actor_map']['test_shadow4:button'] in actors2[2]
        actual2 = utils.report(rt2, result['actor_map']['test_shadow4:bell'])
        assert len(actual2) > len(actual)
        assert all([y-x > 0 for x, y in zip(actual2, actual2[1:])])

        utils.delete_application(rt1, result['application_id'])


    @pytest.mark.slow
    def testDeploy3NodesProxyStorageComponentMoveAllAgain(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global rt3
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_shadow5.calvin"), attr=None,
                                reqs=test_script_dir+"test_shadow4.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        #print "RESULT:", result
        time.sleep(2)

        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow5:button:first'] in actors[1]
        assert result['actor_map']['test_shadow5:button:second'] in actors[1]
        assert result['actor_map']['test_shadow5:check'] in actors[0]
        assert result['actor_map']['test_shadow5:bell'] in actors[2]

        actual = utils.report(rt3, result['actor_map']['test_shadow5:bell'])
        assert len(actual) > 5
        utils.migrate_app_use_req(rt3, result['application_id'],
                            {
                                "requirements": {
                                    "button": [
                                        {
                                          "op": "node_attr_match",
                                            "kwargs": {"index": ["address", {"locality": "inside"}]},
                                            "type": "+"
                                       }],
                                        "bell": [
                                        {
                                            "op": "node_attr_match",
                                            "kwargs": {"index": ["address", {"locality": "outside"}]},
                                            "type": "+"
                                        }],
                                        "check": [
                                        {
                                            "op": "node_attr_match",
                                            "kwargs": {"index": ["node_name", {"name": "display"}]},
                                            "type": "+"
                                        }]
                                }
                            })
        time.sleep(1)
        actors2 = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        assert result['actor_map']['test_shadow5:bell'] in actors2[1]
        assert result['actor_map']['test_shadow5:check'] in actors[0]
        assert result['actor_map']['test_shadow5:button:first'] in actors2[2]
        assert result['actor_map']['test_shadow5:button:second'] in actors2[2]
        actual2 = utils.report(rt2, result['actor_map']['test_shadow5:bell'])
        assert len(actual2) > len(actual)
        assert all([y-x > 0 for x, y in zip(actual2, actual2[1:])])

        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testDeploy3NodesProxyStorageMoveManyTimes(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global rt3
        global test_script_dir

        self.verify_storage()

        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs', 'check'])
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(test_script_dir+"test_deploy1.calvin"), attr=None,
                                reqs=test_script_dir+"test_deploy4.deployjson", check=False)
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        print "RESULT:", result
        time.sleep(2)

        assert result['requirements_fulfilled']

        actors = [utils.get_actors(rt1), utils.get_actors(rt2), utils.get_actors(rt3)]
        # src -> rt1, sum -> rt1, snk -> rt2
        assert result['actor_map']['test_deploy1:src'] in actors[1]
        assert result['actor_map']['test_deploy1:sum'] in actors[0]
        assert result['actor_map']['test_deploy1:snk'] in actors[1]

        for i in range(10):
            utils.migrate_app_use_req(rt1, result['application_id'],
                             {"requirements":
                                {"snk":
                                    [{"op": "node_attr_match",
                                     "kwargs": {"index": ["node_name", {"name": "mtrx"}]},
                                     "type": "+"
                                     }]
                                }
                            }, move=False)
            time.sleep(1)
            actors = utils.get_actors(rt3)
            assert result['actor_map']['test_deploy1:snk'] in actors
            utils.migrate_app_use_req(rt1, result['application_id'],
                             {"requirements":
                                {"snk":
                                    [{"op": "node_attr_match",
                                     "kwargs": {"index": ["node_name", {"name": "serv"}]},
                                     "type": "+"
                                     }]
                                }
                            }, move=False)
            time.sleep(1)
            actors = utils.get_actors(rt2)
            assert result['actor_map']['test_deploy1:snk'] in actors

        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    @pytest.mark.essential
    def testRemoteToRemoteReplicaIsAddedToApplicationsActors(self):
        global rt1
        global rt2
        global rt1_id
        global rt2_id
        self.verify_storage()
        rt = rt1
        peer = rt2
        rt.id = rt1_id
        peer.id = rt2_id

        script = """
            src : std.CountTimer()
            snk : io.StandardOut(store_tokens=1)
            src.integer > snk.token
        """
        app_info, errors, warnings = compiler.compile(script, "simple")
        d = deployer.Deployer(rt, app_info)
        app_id = d.deploy()

        time.sleep(0.2)

        snk = d.actor_map['simple:snk']
        utils.migrate(rt, snk, rt2_id)
        time.sleep(0.2)
        replica = utils.replicate(peer, snk, rt2_id)
        time.sleep(0.2)

        app = utils.get_application(rt, app_id)
        assert replica in app['actors']
        assert replica in app['actors_name_map']

        app = utils.get_application(peer, app_id)
        assert replica in app['actors']
        assert replica in app['actors_name_map']

        d.destroy()
