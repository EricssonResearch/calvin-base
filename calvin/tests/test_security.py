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
from calvin.utilities.nodecontrol import dispatch_node, dispatch_storage_node
from calvin.utilities import calvinuuid
from calvin.utilities.security import Security
from warnings import warn
from calvin.utilities.attribute_resolver import format_index_string
import socket
import os
import json
import copy
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

security_test_dir = None

def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


@pytest.mark.slow
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        global rt1
        global rt2
        global security_test_dir
        security_test_dir = absolute_filename('security_test/')
        
        rt1_conf = copy.deepcopy(_conf)
        rt1_conf.add_section("security")
        rt1_conf.set("security", "security_conf", {
                        "comment": "Experimental security settings",
                        "signature_trust_store": security_test_dir + "keys/app_signer/truststore/",
                        "access_control_enabled": "False",
                        "authentication_method":"local_file",
                        "authentication_local_users": {"user1": "pass1", "user2": "pass2"}
                    })
        rt1_conf.set("security", "security_policy", {
                        "policy1":{
                            "principal":{
                                "user":["user1","user2"],
                                "role":["owner"]
                            },
                            "application_signature": ["signer"],
                            "actor_signature":["signer"],
                            "resource":["calvinsys", "runtime"]
                        },
                        "policy2":{
                            "principal":{
                                "role":["cleaner"],
                                "group":["everyone"]
                            },
                            "application_signature": ["signer"],
                            "component_signature":["signer"],
                            "actor_signature":["signer"],
                            "resource":["calvinsys.events.timer", "runtime"]
                        },
                        "policy3":{
                            "principal":{
                                "group":["everyone"]
                            },
                            "application_signature": ["signer"],
                            "component_signature":["signer"],
                            "actor_signature":["signer"],
                            "resource":["runtime"]
                        }
                    })
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
        rt2_conf.add_section("security")
        rt2_conf.set("security", "security_conf", {
                        "comment": "Experimental security settings",
                        "signature_trust_store": security_test_dir + "keys/app_signer/truststore/",
                        "access_control_enabled": "True",
                        "authentication_method":"local_file",
                        "authentication_local_users": {"user1": "pass1", "user2": "pass2"}
                    })
        rt2_conf.set("security", "security_policy", {
                        "policy1":{
                            "principal":{
                                "user":["user1","user2"],
                                "role":["owner"]
                            },
                            "application_signature": ["__unsigned__"],
                            "actor_signature":["signer"],
                            "resource":["calvinsys", "runtime"]
                        },
                        "policy2":{
                            "principal":{
                                "role":["cleaner"],
                                "group":["everyone"]
                            },
                            "application_signature": ["signer"],
                            "component_signature":["signer"],
                            "actor_signature":["signer"],
                            "resource":["calvinsys.events.timer", "runtime"]
                        },
                        "policy3":{
                            "principal":{
                                "group":["everyone"]
                            },
                            "application_signature": ["signer"],
                            "component_signature":["signer"],
                            "actor_signature":["signer"],
                            "resource":["runtime"]
                        }
                    })
        rt2_conf.set('global', 'actor_paths', [security_test_dir + "/store"])
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

        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt1
        global rt2
        utils.quit(rt1)
        utils.quit(rt2)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        os.system("pkill -9 -f -l 'csruntime -n %s -p 5000'" % (ip_addr,))
        os.system("pkill -9 -f -l 'csruntime -n %s -p 5001'" % (ip_addr,))
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
        for i in range(20):
            try:
                if len(caps1) != 2:
                    caps1 = utils.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if len(caps2) != 2:
                    caps2 = utils.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if len(caps1) == 2 and len(caps2) == 2:
                    failed = False
                    break
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        assert not failed
        _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})
        assert utils.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        _log.analyze("TESTRUN", "+ RT1 INDEX", {})
        assert utils.get_index(rt2, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
        _log.analyze("TESTRUN", "+ RT2 INDEX", {})

    @pytest.mark.slow
    def testSecurityAppSign(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(security_test_dir + "/scripts/test_security1.calvin")
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = utils.deploy_application(rt1, "test_security1", content['file'], 
                        credentials={"user": ["user1"], "password": ["pass1"]}, content=content, 
                        check=True)
        except Exception as e:
            if e.message == "401":
                raise Exception("Failed security verification of app test_security1")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1, no use to verify if requirements fulfilled")
        #print "RESULT:", result
        time.sleep(2)

        # For example verify that actors exist like this
        actors = utils.get_actors(rt1)
        assert result['actor_map']['test_security1:src'] in actors
        assert result['actor_map']['test_security1:sum'] in actors
        assert result['actor_map']['test_security1:snk'] in actors

        actual = utils.report(rt1, result['actor_map']['test_security1:snk'])
        assert len(actual) > 5

        utils.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testSecurityAppUnsigned(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(security_test_dir + "/scripts/test_security1.calvin")
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = utils.deploy_application(rt2, "test_security1", content['file'], 
                        credentials={"user": ["user1"], "password": ["pass1"]}, content=None, 
                        check=True)
        except Exception as e:
            if e.message == "401":
                raise Exception("Failed security verification of app test_security1")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1, no use to verify if requirements fulfilled")
        #print "RESULT:", result
        time.sleep(2)

        # For example verify that actors exist like this
        actors = utils.get_actors(rt2)
        assert result['actor_map']['test_security1:src'] in actors
        assert result['actor_map']['test_security1:sum'] in actors
        assert result['actor_map']['test_security1:snk'] in actors

        actual = utils.report(rt2, result['actor_map']['test_security1:snk'])
        assert len(actual) > 5

        utils.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurityAppFailSign(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global rt2
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(security_test_dir + "/scripts/test_security1.calvin")
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = utils.deploy_application(rt1, "test_security1", content['file'], 
                        credentials={"user": ["user3"], "password": ["pass1"]}, content=content, 
                        check=True)
        except Exception as e:
            if e.message == "401":
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1, did not fail for security reasons")

