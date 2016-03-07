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
import pytest
import socket
import os
import shutil
import json
from calvin.requests.request_handler import RequestHandler, RT
from calvin.utilities.nodecontrol import dispatch_node, dispatch_storage_node
from calvin.utilities.attribute_resolver import format_index_string
from calvin.utilities import certificate
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
from calvin.utilities import calvinuuid

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()
request_handler = RequestHandler()

try:
    ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
except:
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
class TestSecureDht(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        homefolder = os.getenv("HOME")
        domain = "rttest"
        configdir = os.path.join(homefolder, ".calvin",
                                       "security", domain)
        try:
            shutil.rmtree(configdir)
        except:
            pass
        print "Trying to create a new test domain configuration."
        testconfig = certificate.Config(domain=domain)
        print "Reading configuration successfull."

        print "Creating new domain."
        certificate.new_domain(testconfig)
        print "Created new domain."
        # Now handled within runtime
        #for i in range(3):
        #    name = "++++node{}".format(i)
        #    nodeid = calvinuuid.uuid("NODE")
        #    certreq = certificate.new_runtime(testconfig, name, nodeid=nodeid)
        #    certificate.sign_req(testconfig, os.path.basename(certreq), name)

        global rt1
        global rt2
        global rt3
        global test_script_dir
        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('global', 'storage_type', 'securedht')
        rt_conf.add_section('security')
        rt_conf.set('security', "certificate_conf", None)
        rt_conf.set('security', "certificate_domain", domain)
        rt_conf.save("/tmp/calvin500x.conf")
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
                   'node_name': {'name': 'node0'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin500x.conf")
        rt1 = RT("http://%s:5003" % ip_addr)
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
                   'node_name': {'name': 'node1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin500x.conf")
        rt2 = RT("http://%s:5004" % ip_addr)
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
                   'node_name': {'name': 'node2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin500x.conf")
        rt3 = RT("http://%s:5005" % ip_addr)

        test_script_dir = absolute_filename('scripts/')
        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt1
        global rt2
        global rt3
        request_handler.quit(rt1)
        request_handler.quit(rt2)
        request_handler.quit(rt3)
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
        # Try 30 times waiting for control API to be up and running
        for i in range(30):
            try:
                rt1_id = rt1_id or request_handler.get_node_id(rt1)
                rt2_id = rt2_id or request_handler.get_node_id(rt2)
                rt3_id = rt3_id or request_handler.get_node_id(rt3)
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
        # Try 30 times waiting for storage to be connected
        caps1 = []
        caps2 = []
        caps3 = []
        rt_ids = set([rt1_id, rt2_id, rt3_id])
        for i in range(30):
            try:
                if not (rt1_id in caps1 and rt2_id in caps1 and rt3_id in caps1):
                    caps1 = request_handler.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps2 and rt2_id in caps2 and rt3_id in caps2):
                    caps2 = request_handler.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps3 and rt2_id in caps3 and rt3_id in caps3):
                    caps3 = request_handler.get_index(rt3, "node/capabilities/calvinsys.native.python-json")['result']
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
        caps = request_handler.get_index(rt1, 'node/capabilities/calvinsys.events.timer')
        assert rt1_id in caps['result']
        _log.analyze("TESTRUN", "+ RT1 CAPS", {})
        caps = request_handler.get_index(rt2, 'node/capabilities/calvinsys.events.timer')
        assert rt1_id in caps['result']
        _log.analyze("TESTRUN", "+ RT2 CAPS", {})
        assert request_handler.get_index(rt1, format_index_string(['node_name', {'name': 'node2'}]))
        _log.analyze("TESTRUN", "+ RT1 INDEX", {})
        assert request_handler.get_index(rt2, format_index_string(['node_name', {'name': 'node1'}]))
        _log.analyze("TESTRUN", "+ RT2 INDEX", {})

    @pytest.mark.slow
    def testSecureDHTVerifyStorage(self):
        _log.analyze("TESTRUN", "+", {})

        self.verify_storage()


    """
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
        request_handler.migrate(rt2, result['actor_map']['test_shadow1:snk'], rt1_id)
        time.sleep(1)

        actors = [request_handler.get_actors(rt1), request_handler.get_actors(rt2), request_handler.get_actors(rt3)]
        # src -> rt2, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[1]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]

        actual = request_handler.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) == 0
        request_handler.migrate(rt2, result['actor_map']['test_shadow1:src'], rt3_id)
        time.sleep(1)
        actors = [request_handler.get_actors(rt1), request_handler.get_actors(rt2), request_handler.get_actors(rt3)]
        # src -> rt3, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[2]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]
        actual = request_handler.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) == 0
        request_handler.migrate(rt3, result['actor_map']['test_shadow1:src'], rt1_id)
        time.sleep(1)
        actors = [request_handler.get_actors(rt1), request_handler.get_actors(rt2), request_handler.get_actors(rt3)]
        # src -> rt1, sum -> rt2, snk -> rt1
        assert result['actor_map']['test_shadow1:src'] in actors[0]
        assert result['actor_map']['test_shadow1:sum'] in actors[1]
        assert result['actor_map']['test_shadow1:snk'] in actors[0]
        actual = request_handler.report(rt1, result['actor_map']['test_shadow1:snk'])
        assert len(actual) > 3

        request_handler.delete_application(rt2, result['application_id'])

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
        request_handler.delete_application(rt2, result['application_id'])

    """