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
import pytest
from requests.exceptions import Timeout
from calvin.requests.request_handler import RequestHandler, RT
from calvin.utilities.nodecontrol import dispatch_node, dispatch_storage_node
from calvin.utilities.security import Security
from calvin.utilities.attribute_resolver import format_index_string
import os
import json
import copy
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()
request_handler = RequestHandler()

try:
    ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
except:
    import socket
    ip_addr = socket.gethostbyname(socket.gethostname())

rt1 = None
rt2 = None
rt3 = None
rt4 = None

security_test_dir = None


@pytest.mark.slow
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        global rt1
        global rt2
        global rt3
        global rt4
        global security_test_dir
        security_test_dir = os.path.join(os.path.dirname(__file__), "security_test")

        # Runtime 1: local authentication, signature verification, local authorization.
        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'security_domain_name', "testdomain")
        rt_conf.set('security', 'security_path',security_test_dir)
        rt_conf.set('global', 'actor_paths', [os.path.join(security_test_dir, "store")])
        rt1_conf = copy.deepcopy(rt_conf)
        rt1_conf.set("security", "security_conf", {
                        "comment": "Local authentication, local authorization",
                        "signature_trust_store": os.path.join(security_test_dir, "trustStore"),
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": os.path.join(security_test_dir, "identity_provider")
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": os.path.join(security_test_dir, "policies")
                        }
                    })
        rt1_conf.set('global', 'actor_paths', [os.path.join(security_test_dir, "store")])
        rt1_conf.save("/tmp/calvin5001.conf")

        try:
            logfile = _config_pytest.getoption("logfile")+"5001"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5001, controlport=5021, attr={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5001.conf")
        rt1 = RT("http://%s:5021" % ip_addr)


        # Runtime 2: local authentication, signature verification, local authorization.
        # Can also act as authorization server for other runtimes.
        # Other street compared to the other runtimes
        rt2_conf = copy.deepcopy(rt_conf)
        rt2_conf.set("security", "security_conf", {
                        "comment": "Local authentication, local authorization",
                        "signature_trust_store": os.path.join(security_test_dir, "trustStore"),
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": os.path.join(security_test_dir, "identity_provider")
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": os.path.join(security_test_dir, "policies"),
                            "accept_external_requests": True
                        }
                    })
        rt2_conf.set('global', 'actor_paths', [os.path.join(security_test_dir, "store")])
        rt2_conf.save("/tmp/calvin5002.conf")

        try:
            logfile = _config_pytest.getoption("logfile")+"5002"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5002, controlport=5022, attr={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'otherStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5002.conf")
        rt2 = RT("http://%s:5022" % ip_addr)


        # Runtime 3: external authentication (RADIUS), signature verification, local authorization.
        rt3_conf = copy.deepcopy(rt_conf)
        rt3_conf.set("security", "security_conf", {
                        "comment": "RADIUS authentication, local authorization",
                        "signature_trust_store": os.path.join(security_test_dir, "trustStore"),
                        "authentication": {
                            "procedure": "radius", 
                            "server_ip": "localhost", 
                            "secret": "elxghyc5lz1_passwd"
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": os.path.join(security_test_dir, "policies")
                        }
                    })
        rt3_conf.set('global', 'actor_paths', [os.path.join(security_test_dir, "store")])
        rt3_conf.save("/tmp/calvin5003.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5003"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(ip_addr, port=5003, controlport=5023, attr={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode3'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5003.conf")
        rt3 = RT("http://%s:5023" % ip_addr)


        # Runtime 4: local authentication, signature verification, external authorization (runtime 2).
        rt4_conf = copy.deepcopy(rt_conf)
        rt4_conf.set("security", "security_conf", {
                        "comment": "Local authentication, external authorization",
                        "signature_trust_store": os.path.join(security_test_dir, "trustStore"),
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": os.path.join(security_test_dir, "identity_provider")
                        },
                        "authorization": {
                            "procedure": "external",
                            "server_uuid": "17e9ad66-bcba-4068-bc17-7fcc86aa870e"
                        }
                    })
        rt4_conf.set('global', 'actor_paths', [os.path.join(security_test_dir, "store")])
        rt4_conf.save("/tmp/calvin5004.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5004"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        time.sleep(1)  # Wait to be sure that runtime 2 has started
        csruntime(ip_addr, port=5004, controlport=5024, attr={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode4'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}},
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5004.conf")
        rt4 = RT("http://%s:5024" % ip_addr)

        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt1
        global rt2
        global rt3
        global rt4
        request_handler.quit(rt1)
        request_handler.quit(rt2)
        request_handler.quit(rt3)
        request_handler.quit(rt4)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        os.system("pkill -9 -f 'csruntime -n %s -p 5001'" % (ip_addr,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5002'" % (ip_addr,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5003'" % (ip_addr,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5004'" % (ip_addr,))
        time.sleep(0.2)

    def verify_storage(self):
        global rt1
        global rt2
        global rt3
        global rt4
        rt1_id = None
        rt2_id = None
        rt3_id = None
        rt4_id = None
        failed = True
        # Try 30 times waiting for control API to be up and running
        for i in range(30):
            try:
                rt1_id = rt1_id or request_handler.get_node_id(rt1)
                rt2_id = rt2_id or request_handler.get_node_id(rt2)
                rt3_id = rt3_id or request_handler.get_node_id(rt3)
                rt4_id = rt4_id or request_handler.get_node_id(rt4)
                failed = False
                break
            except:
                time.sleep(0.1)
        assert not failed
        assert rt1_id
        assert rt2_id
        assert rt3_id
        assert rt4_id
        print "RUNTIMES:", rt1_id, rt2_id, rt3_id, rt4_id
        _log.analyze("TESTRUN", "+ IDS", {'waited': 0.1*i})
        failed = True
        # Try 30 times waiting for storage to be connected
        caps1 = []
        caps2 = []
        caps3 = []
        caps4 = []
        rt_ids = set([rt1_id, rt2_id, rt3_id, rt4_id])
        for i in range(30):
            try:
                if not (rt1_id in caps1 and rt2_id in caps1 and rt3_id in caps1 and rt4_id in caps1):
                    caps1 = request_handler.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps2 and rt2_id in caps2 and rt3_id in caps2 and rt4_id in caps2):
                    caps2 = request_handler.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps3 and rt2_id in caps3 and rt3_id in caps3 and rt4_id in caps3):
                    caps3 = request_handler.get_index(rt3, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt1_id in caps4 and rt2_id in caps4 and rt3_id in caps4 and rt4_id in caps4):
                    caps4 = request_handler.get_index(rt4, "node/capabilities/calvinsys.native.python-json")['result']
                if rt_ids <= set(caps1) and rt_ids <= set(caps2) and rt_ids <= set(caps3) and rt_ids <= set(caps4):
                    failed = False
                    break
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        assert not failed
        _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})
        assert request_handler.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
        _log.analyze("TESTRUN", "+ RT1 INDEX", {})
        assert request_handler.get_index(rt2, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        _log.analyze("TESTRUN", "+ RT2 INDEX", {})
        assert request_handler.get_index(rt3, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode3'}]))
        _log.analyze("TESTRUN", "+ RT3 INDEX", {})
        assert request_handler.get_index(rt4, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode4'}]))
        _log.analyze("TESTRUN", "+ RT4 INDEX", {})


###################################
#   Signature related tests
###################################

    @pytest.mark.slow
    def testSecurity_POSITIVE_CorrectlySignedApp_CorrectlySignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt1, "test_security1_correctly_signed", content['file'], 
                    credentials={"testdomain":{"user": "user1", "password": "pass1"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt1)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt1, result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testSecurity_NEGATIVE_IncorrectlySignedApp(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_incorrectly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt1, "test_security1_incorrectly_signed", content['file'], 
                    credentials={"testdomain":{"user": "user1", "password": "pass1"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")

    @pytest.mark.slow
    def testSecurity_NEGATIVE_CorrectlySignedApp_IncorrectlySignedActor(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_correctlySignedApp_incorrectlySignedActor.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt1, "test_security1_correctlySignedApp_incorrectlySignedActor", content['file'], 
                    credentials={"testdomain":{"user": "user1", "password": "pass1"}}, content=content, 
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctlySignedApp_incorrectlySignedActor")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctlySignedApp_incorrectlySignedActor, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt1)
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:src'] in actors
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:sum'] in actors
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'] in actors

        actual = request_handler.report(rt1, result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'])
        assert len(actual) == 0  # Means that the incorrectly signed actor was not accepted

        request_handler.delete_application(rt1, result['application_id'])


###################################
#   Policy related tests
###################################

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_SignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt2, "test_security1_unsignedApp_signedActors", content['file'], 
                        credentials={"testdomain":{"user":"user2", "password":"pass2"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt2)
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors

        actual = request_handler.report(rt2, result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_Unsigned_Actor(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_unsignedApp_unsignedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt2, "test_security1_unsignedApp_unsignedActors", content['file'], 
                        credentials={"testdomain":{"user":"user3", "password":"pass3"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_unsignedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt2)
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors

        actual = request_handler.report(rt2, result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurity_NEGATIVE_Deny_SignedApp_SignedActor_UnallowedRequirement(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt2, "test_security1_correctly_signed", content['file'], 
                        credentials={"testdomain":{"user":"user1", "password":"pass1"}}, content=content, 
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt2)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt2, result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) == 0  # Means that the actor with unallowed requirements was not accepted

        request_handler.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_External_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global rt4
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt4, "test_security1_unsignedApp_signedActors", content['file'], 
                        credentials={"testdomain":{"user":"user2","password":"pass2"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt4)
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors

        actual = request_handler.report(rt4, result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt4, result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Migration_When_Denied(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global rt4
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt2, "test_security1_correctly_signed", content['file'], 
                        credentials={"testdomain":{"user":"user4", "password":"pass4"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this (all of them should have migrated to rt4)
        actors = request_handler.get_actors(rt4)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt4, result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt2, result['application_id'])


###################################
#   Authentication related tests
###################################

    @pytest.mark.slow
    def testSecurity_NEGATIVE_UnallowedUser(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt1, "test_security1_correctly_signed", content['file'], 
                        credentials={"testdomain":{"user":"user_not_allowed", "password":"pass1"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed did not fail for security reasons")  

    @pytest.mark.slow
    def testSecurity_NEGATIVE_IncorrectPassword(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt1, "test_security1_correctly_signed", content['file'], 
                        credentials={"testdomain":{"user":"user1", "password":"incorrect_password"}}, content=content, 
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")  

    #This only works if a properly configured RADIUS server is available on localhost
    @pytest.mark.xfail
    @pytest.mark.slow
    def testSecurity_POSITIVE_RADIUS_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        global rt3
        global security_test_dir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(security_test_dir, "scripts", "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            result = request_handler.deploy_application(rt3, "test_security1_correctly_signed", content['file'], 
                        credentials={"testdomain":{"user":"user5", "password":"pass5"}}, content=content, 
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to RADIUS server. Have you started a RADIUS server?")
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt3)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt3, result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt3, result['application_id'])
