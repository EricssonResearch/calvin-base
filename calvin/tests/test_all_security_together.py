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
import shutil
import multiprocessing
import pytest
import os
from copy import deepcopy
from requests.exceptions import Timeout
from calvin.requests.request_handler import RequestHandler, RT
from calvin.utilities.nodecontrol import dispatch_node, dispatch_storage_node
from calvin.utilities.security import Security
from calvin.utilities import certificate
from calvin.utilities import certificate_authority
from calvin.utilities import code_signer
from calvin.utilities import runtime_credentials
from calvin.utilities.attribute_resolver import format_index_string
from calvin.utilities.utils import get_home
from calvin.utilities.attribute_resolver import AttributeResolver
from calvin.utilities import calvinuuid
from calvin.runtime.north.authentication.authentication_retrieval_point import FileAuthenticationRetrievalPoint
from . import helpers

import os
import json
import copy
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

homefolder = get_home()
credentials_testdir = os.path.join(homefolder, ".calvin","test_all_security_together_dir")
runtimesdir = os.path.join(credentials_testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")
runtimes_truststore_signing_path = os.path.join(runtimesdir,"truststore_for_signing")
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="test_security_domain"
code_signer_name="test_signer"
org_name='org.testexample'
orig_identity_provider_path = os.path.join(security_testdir,"identity_provider")
identity_provider_path = os.path.join(credentials_testdir, "identity_provider")
policy_storage_path = os.path.join(security_testdir, "policies")
orig_actor_store_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'actorstore','systemactors'))
actor_store_path = os.path.join(credentials_testdir, "store")
orig_application_store_path = os.path.join(security_testdir, "scripts")
application_store_path = os.path.join(credentials_testdir, "scripts")

NBR_OF_RUNTIMES=3

try:
    ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
except:
    import socket
    # If this fails add hostname to the /etc/hosts file for 127.0.0.1
    ip_addr = socket.gethostbyname(socket.gethostname())
    hostname = socket.gethostname()

rt=[]
rt_attributes=[]
request_handler=None
storage_verified=False

@pytest.mark.slow
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        import fileinput
        global rt
        global rt_attributes
        global request_handler
        try:
            shutil.rmtree(credentials_testdir)
        except Exception as err:
            print "Failed to remove old tesdir, err={}".format(err)
            pass
        try:
            shutil.copytree(orig_identity_provider_path, identity_provider_path)
        except Exception as err:
            _log.error("Failed to create test folder structure, err={}".format(err))
            print "Failed to create test folder structure, err={}".format(err)
            raise
        helpers.sign_files_for_security_tests(credentials_testdir)

        print "Trying to create a new test domain configuration."
        ca = certificate_authority.CA(domain=domain_name, commonName="testdomain CA", security_dir=credentials_testdir)
#
        print "Copy CA cert into truststore of runtimes folder"
        ca.export_ca_cert(runtimes_truststore)
        certificate.c_rehash(type=certificate.TRUSTSTORE_TRANSPORT, security_dir=credentials_testdir)

        #Define the runtime attributes
        for i in range(NBR_OF_RUNTIMES):
            purpose = 'CA-authserver-authzserver' if i==0 else ""
            node_name ={'organization': org_name,
                         'purpose':purpose,
                         'name': 'testNode{}'.format(i)}
            owner = {'organization': domain_name, 'personOrGroup': 'testOwner'}
            address = {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}
            rt_attribute=  {
                                'indexed_public':
                                {
                                    'owner':owner,
                                    'node_name':node_name,
                                    'address':address
                                }
                            }
            rt_attributes.append(rt_attribute)
        rt_attributes_cpy = deepcopy(rt_attributes)

        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)
        #Let's use the admin user0 for request_handler 
        request_handler.set_credentials({"user": "user0", "password": "pass0"})

        #####################
        # Runtime 0: Certificate authority, authentication server, authorization server.
        #####################
        #Generate credentials, create CSR, sign with CA and import cert for all runtimes
        enrollment_passwords=[]
        attributes=AttributeResolver(rt_attributes_cpy[0])
        node_name = attributes.get_node_name_as_str()
        #rt0 need authzserver extension to it's node name, which needs to be certified by the CA
        ca.add_new_authentication_server(node_name)
        ca.add_new_authorization_server(node_name)
        #Just add an empty item for maintaining the same length for the list
        enrollment_passwords.append("")

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])
        rt_conf.set('global', 'storage_type', "securedht")

        # Runtime 0: Certificate authority, authentication server, authorization server.
        rt0_conf = copy.deepcopy(rt_conf)
        rt0_conf.set('security', 'control_interface_security', "tls")
        rt0_conf.set('security','certificate_authority',{
                        'domain_name':domain_name,
                        'is_ca':'True'
                    })
        rt0_conf.set("security", "security_conf", {
                        "comment": "Certificate Authority",
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": identity_provider_path,
                            "accept_external_requests": "True"
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": policy_storage_path,
                            "accept_external_requests": "True"
                        }
                    })
        rt0_conf.save("/tmp/calvin5000.conf")

        #Start runtime 0 as it takes alot of time to start, and needs to be up before the others start
        _log.info("Starting runtime 0")
        try:
            logfile = _config_pytest.getoption("logfile")+"5000"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(hostname, port=5000, controlport=5020, attr=rt_attributes[0],
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5000.conf")
        rt.append(RT("https://{}:5020".format(hostname)))
        rt[0].attributes=rt_attributes[0]

        #####################
        #Other runtimes:
        #####################
        for i in range(1, NBR_OF_RUNTIMES):
            attributes=AttributeResolver(rt_attributes_cpy[i])
            node_name = attributes.get_node_name_as_str()
            #Alt 1
#            enrollment_password = ca.cert_enrollment_add_new_runtime(node_name)
            #Alt 2
#            enrollment_password = request_handler.get_enrollment_password(rt[0], node_name)
            #Alt 3
            enrollment_password = "abrakadabra123456789"
            enrollment_passwords.append(enrollment_password)
            for j in range(1, 100):
                try:
                    request_handler.set_enrollment_password(rt[0], node_name, enrollment_password)
                    break
                except:
                    _log.error("Set enrollment password, still no reply from CA, i={} j={}".format(i, j))
                    time.sleep(0.5)
                    continue

        # Other runtimes: external authentication, external authorization.
        rt_conf.set("security", "security_conf", {
                        "comment": "External authentication, external authorization",
                        "authentication": {
                            "procedure": "external"
                        },
                        "authorization": {
                            "procedure": "external"
                        }
                    })

        for i in range(1, NBR_OF_RUNTIMES):
            rt_conf.set('security','certificate_authority',{
                            'domain_name':domain_name,
                            'is_ca':'False',
                            'ca_control_uri':"https://%s:5020" % hostname,
                            'enrollment_password':enrollment_passwords[i]
                        })
            rt_conf.save("/tmp/calvin500{}.conf".format(i))

#        # Runtime 3: external authentication (RADIUS).
#        rt3_conf = copy.deepcopy(rt1_conf)
#        rt3_conf.set('security','enrollment_password',enrollment_passwords[3])
#        rt3_conf.save("/tmp/calvin5002.conf")
#        rt3_conf.set("security", "security_conf", {
#                        "authentication": {
#                            "procedure": "radius",
#                            "server_ip": "localhost",
#                            "secret": "elxghyc5lz1_passwd"
#                        },
#                        "authorization": {
#                            "procedure": "external",
#                            "server_uuid": runtimes[0].node_id
#                        }
#                    })
#        rt3_conf.save("/tmp/calvin5003.conf")


        #Start the other runtimes
        for i in range(1, NBR_OF_RUNTIMES):
            _log.info("Starting runtime {}".format(i))
            try:
                logfile = _config_pytest.getoption("logfile")+"500{}".format(i)
                outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
                if outfile == logfile:
                    outfile = None
            except:
                logfile = None
                outfile = None
            csruntime(hostname, port=5000+i, controlport=5020+i, attr=rt_attributes[i],
                       loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                       configfile="/tmp/calvin500{}.conf".format(i))
            rt.append(RT("https://{}:502{}".format(hostname,i)))
            rt[i].attributes=rt_attributes[i]
            time.sleep(0.1)
        request.addfinalizer(self.teardown)


    def teardown(self):
        _log.info("-----------------teardown----------------------")
        global rt
        global request_handler
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        for i in range(1, NBR_OF_RUNTIMES):
            _log.info("kill runtime {}".format(i))
            request_handler.quit(rt[i])
        # Kill storage node last since the othernodes might be a need to lookup 
        # certificates (if they have not contacted the authentication server previously)
        # to actually kill the node
        time.sleep(1)
        request_handler.quit(rt[0])
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        for i in range(NBR_OF_RUNTIMES):
            os.system("pkill -9 -f 'csruntime -n {} -p 500{}'" .format(hostname,i))
        time.sleep(0.2)


###################################
#   Signature related tests
###################################

    @pytest.mark.slow
    def testSecurity_POSITIVE_CorrectlySignedApp_CorrectlySignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[1]
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        actual = request_handler.report(rt[1], result['actor_map']['test_security1_correctly_signed:snk'])
        print "actual=", actual
        assert len(actual) > 2

        request_handler.delete_application(rt[1], result['application_id'])


    @pytest.mark.slow
    def testSecurity_NEGATIVE_IncorrectlySignedApp(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_incorrectly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(rt[1], "test_security1_incorrectly_signed", content['file'], 
                        content=content,
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
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctlySignedApp_incorrectlySignedActor.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctlySignedApp_incorrectlySignedActor", content['file'], 
                    credentials={domain_name:{"user": "user1", "password": "pass1"}}, content=content,
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctlySignedApp_incorrectlySignedActor")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctlySignedApp_incorrectlySignedActor, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:src'] in actors[1]
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:sum'] in actors[1]
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'])
        assert len(actual) == 0  # Means that the incorrectly signed actor was not accepted

        request_handler.delete_application(rt[1], result['application_id'])


###################################
#   Policy related tests
###################################

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_SignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(rt[1], "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(rt[1], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_Unsigned_Actor(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_unsignedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user3", "password": "pass3"})
            result = request_handler.deploy_application(rt[1], "test_security1_unsignedApp_unsignedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_unsignedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(rt[1], result['application_id'])

    @pytest.mark.slow
    def testSecurity_NEGATIVE_Deny_SignedApp_SignedActor_UnallowedRequirement(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(rt[2], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[2]

        actual = request_handler.report(rt[2], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) == 0  # Means that the actor with unallowed requirements was not accepted

        request_handler.delete_application(rt[2], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Local_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(rt[0], "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors[0]

        actual = request_handler.report(rt[0], result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(rt[0], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_External_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(rt[1], "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(rt[1], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Migration_When_Denied(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user4", "password": "pass4"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this (all of them should have migrated to rt[2])
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[2]

        actual = request_handler.report(rt[2], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 2

        request_handler.delete_application(rt[1], result['application_id'])

###################################
#   Control interface authorization 
#   as well as user db management
###################################

    @pytest.mark.slow
    def testSecurity_NEGATIVE_Control_Interface_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user6", "password": "pass6"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'],
                                                        content=content,
                                                        check=True,
                                                        timeout=15.0)
        except Timeout as err:
            _log.error("Timeout while trying to deploy application, err={}".format(err))
            raise
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.error("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")

    @pytest.mark.slow
    def testSecurity_POSITIVE_Add_User(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        users_db=None
        try:
            request_handler.set_credentials({"user": "user0", "password": "pass0"})
            users_db = request_handler.get_users_db(rt[0])
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        if users_db:
            #TODO: seem more efficient to have a dictionary instead of a list of users
            users_db['user7']={"username": "user7",
                                        "attributes": {
                                                        "age": "77", 
                                                        "last_name": "Gretasdottir",
                                                        "first_name": "Greta",
                                                        "address": "Mobilvagen 1"
                                                    }, 
                                        "password": "pass7"}
        else:
            raise Exception("users_db not in result or users_db not in result[users_db]")
        #PUT the update database to the authentication server
        try:
            result = request_handler.post_users_db(rt[0], users_db)
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        #Read the users database back again and check if Greta has been added
        try:
            users_db2 = request_handler.get_users_db(rt[0])
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        if not 'user7' in users_db2:
            raise Exception("Failed to update the users_db")


###################################
#   Authentication related tests
###################################

    @pytest.mark.slow
    def testSecurity_NEGATIVE_UnallowedUser(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user_not_allowed", "password": "pass1"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
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
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "incorrect_password"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")  

    @pytest.mark.slow
    def testSecurity_POSITIVE_Local_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = request_handler.deploy_application(rt[0], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 0.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[0]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[0]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[0]

        time.sleep(1)
        actual = request_handler.report(rt[0], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 2

        request_handler.delete_application(rt[0], result['application_id']) 

    @pytest.mark.slow
    def testSecurity_POSITIVE_External_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 5.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[1]

        time.sleep(1)
        actual = request_handler.report(rt[1], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 2

        request_handler.delete_application(rt[1], result['application_id']) 

#    @pytest.mark.xfail
#    @pytest.mark.slow
#    def testSecurity_POSITIVE_RADIUS_Authentication(self):
#        _log.analyze("TESTRUN", "+", {})
#        global rt
#        global request_handler
#        global security_testdir
#        global storage_verified
#        if not storage_verified:
#            try:
#                storage_verified = helpers.security_verify_storage(rt, request_handler)
#            except Exception as err:
#                _log.error("Failed storage verification, err={}".format(err))
#                raise
#
#        result = {}
#        try:
#            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
#            if not content:
#                raise Exception("Failed finding script, signature and cert, stopping here")
#            request_handler.set_credentials({"user": "user5", "password": "pass5"})
#            result = request_handler.deploy_application(rt[3], "test_security1_correctly_signed", content['file'], 
#                        content=content,
#                        check=True)
#        except Exception as e:
#            if isinstance(e, Timeout):
#                raise Exception("Can't connect to RADIUS server. Have you started a RADIUS server?")
#            elif e.message.startswith("401"):
#                raise Exception("Failed security verification of app test_security1_correctly_signed")
#            _log.exception("Test deploy failed")
#            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
#
#        # Verify that actors exist like this
#        try:
#            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
#        except Exception as err:
#            _log.error("Failed to get actors from runtimes, err={}".format(err))
#            raise
#            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
#        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[3]
#        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[3]
#        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[3]
#
#        actual = request_handler.report(rt[3], result['actor_map']['test_security1_correctly_signed:snk'])
#        assert len(actual) > 2
#
#        request_handler.delete_application(rt[3], result['application_id'])
