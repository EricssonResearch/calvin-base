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
credentials_testdir = os.path.join(homefolder, ".calvin","test_authorization_authentication_dir")
runtimesdir = os.path.join(credentials_testdir,"runtimes")
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="test_security_domain"
code_signer_name="test_signer"
orig_identity_provider_path = os.path.join(security_testdir,"identity_provider")
identity_provider_path = os.path.join(credentials_testdir, "identity_provider")
policy_storage_path = os.path.join(security_testdir, "policies")
orig_actor_store_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'actorstore','systemactors'))
actor_store_path = os.path.join(credentials_testdir, "store")
orig_application_store_path = os.path.join(security_testdir, "scripts")
application_store_path = os.path.join(credentials_testdir, "scripts")

NBR_OF_RUNTIMES=3

import socket
from calvin.tests.helpers import get_ip_addr
ip_addr = get_ip_addr()
hostname = socket.gethostname()

runtimes=[]
request_handler=None
storage_verified=False


@pytest.mark.slow
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        import fileinput
        global runtimes
        global request_handler
        try:
            shutil.rmtree(credentials_testdir)
        except Exception as err:
            print "Failed to remove old tesdir, err={}".format(err)
            pass
        try:
            shutil.copytree(orig_identity_provider_path, identity_provider_path)
        except Exception as err:
            _log.error("Failed to copy the identity provider files, err={}".format(err))
            raise
        actor_store_path, application_store_path = helpers.sign_files_for_security_tests(credentials_testdir)
        runtimes = helpers.create_CA_and_generate_runtime_certs(domain_name, credentials_testdir, NBR_OF_RUNTIMES)

        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)
        #Let's use the admin user0 for request_handler
        request_handler.set_credentials({"user": "user0", "password": "pass0"})

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])

        # Runtime 0: Certificate authority, authentication server, authorization server.
        rt0_conf = copy.deepcopy(rt_conf)
        rt0_conf.set('global','storage_type','local')
        rt0_conf.set('security','certificate_authority',{
            'domain_name':domain_name,
            'is_ca':True
            })
        rt0_conf.set("security", "security_conf", {
                        "comment": "Certificate Authority",
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": identity_provider_path,
                            "accept_external_requests": True
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": policy_storage_path,
                            "accept_external_requests": True
                        }
                    })
        rt0_conf.save("/tmp/calvin5000.conf")

        _log.info("Starting runtime 0")

        # Other runtimes
        rt_conf.set('global','storage_type','proxy')
        rt_conf.set('global','storage_proxy',"calvinip://%s:5000" % ip_addr )
        rt_conf.set('security','certificate_authority',{
            'domain_name':domain_name,
            'is_ca':False
        })
        rt_conf.set("security", "security_conf", {
                        "comment": "External authentication, external authorization",
                        "authentication": {
                            "procedure": "external",
                            "server_uuid": runtimes[0]["id"]
                        },
                        "authorization": {
                            "procedure": "external",
                            "server_uuid": runtimes[0]["id"]
                        }
                    })

        for i in range(1, NBR_OF_RUNTIMES):
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

        helpers.start_all_runtimes(runtimes, hostname, request_handler)
        request.addfinalizer(self.teardown)


    def teardown(self):
        helpers.teardown_slow(runtimes, request_handler, hostname)

###################################
#   Signature related tests
###################################

    @pytest.mark.slow
    def testPositive_CorrectlySignedApp_CorrectlySignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['correctly_signed:src'] in actors[1]
        assert result['actor_map']['correctly_signed:sum'] in actors[1]
        assert result['actor_map']['correctly_signed:snk'] in actors[1]
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['correctly_signed:snk'])
        _log.info("actual={}".format(actual))
        assert len(actual) > 2

        request_handler.delete_application(runtimes[1]["RT"], result['application_id'])


    @pytest.mark.slow
    def testNegative_IncorrectlySignedApp(self):
        _log.analyze("TESTRUN", "+", {})

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "incorrectly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "incorrectly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app correctly_signed, did not fail for security reasons")

    @pytest.mark.slow
    def testNegative_CorrectlySignedApp_IncorrectlySignedActor(self):
        _log.analyze("TESTRUN", "+", {})

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctlySignedApp_incorrectlySignedActor.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "correctlySignedApp_incorrectlySignedActor", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctlySignedApp_incorrectlySignedActor")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctlySignedApp_incorrectlySignedActor, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['correctlySignedApp_incorrectlySignedActor:src'] in actors[1]
        assert result['actor_map']['correctlySignedApp_incorrectlySignedActor:sum'] in actors[1]
        assert result['actor_map']['correctlySignedApp_incorrectlySignedActor:snk'] in actors[1]

        actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['correctlySignedApp_incorrectlySignedActor:snk'])
        _log.info("actual={}".format(actual))
        assert len(actual) == 0  # Means that the incorrectly signed actor was not accepted

        request_handler.delete_application(runtimes[1]["RT"], result['application_id'])


###################################
#   Policy related tests
###################################


    @pytest.mark.slow
    def testPositive_Permit_UnsignedApp_SignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['unsignedApp_signedActors:src'] in actors[1]
        assert result['actor_map']['unsignedApp_signedActors:sum'] in actors[1]
        assert result['actor_map']['unsignedApp_signedActors:snk'] in actors[1]

        actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['unsignedApp_signedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(runtimes[1]["RT"], result['application_id'])

    @pytest.mark.slow
    def testPositive_Permit_UnsignedApp_Unsigned_Actor(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_unsignedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user3", "password": "pass3"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "unsignedApp_unsignedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_unsignedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['unsignedApp_unsignedActors:src'] in actors[1]
        assert result['actor_map']['unsignedApp_unsignedActors:sum'] in actors[1]
        assert result['actor_map']['unsignedApp_unsignedActors:snk'] in actors[1]

        actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['unsignedApp_unsignedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(runtimes[1]["RT"], result['application_id'])

    @pytest.mark.slow
    def testNegative_Deny_SignedApp_SignedActor_UnallowedRequirement(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(runtimes[2]["RT"], "correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['correctly_signed:src'] in actors[2]
        assert result['actor_map']['correctly_signed:sum'] in actors[2]
        assert result['actor_map']['correctly_signed:snk'] in actors[2]

        actual = request_handler.report(runtimes[2]["RT"], result['actor_map']['correctly_signed:snk'])
        _log.debug("actual={}".format(actual))
        assert len(actual) == 0  # Means that the actor with unallowed requirements was not accepted

        request_handler.delete_application(runtimes[2]["RT"], result['application_id'])

    @pytest.mark.slow
    def testPositive_Local_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(runtimes[0]["RT"], "unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['unsignedApp_signedActors:src'] in actors[0]
        assert result['actor_map']['unsignedApp_signedActors:sum'] in actors[0]
        assert result['actor_map']['unsignedApp_signedActors:snk'] in actors[0]

        actual = request_handler.report(runtimes[0]["RT"], result['actor_map']['unsignedApp_signedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(runtimes[0]["RT"], result['application_id'])

    @pytest.mark.slow
    def testPositive_External_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['unsignedApp_signedActors:src'] in actors[1]
        assert result['actor_map']['unsignedApp_signedActors:sum'] in actors[1]
        assert result['actor_map']['unsignedApp_signedActors:snk'] in actors[1]

        actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['unsignedApp_signedActors:snk'])
        assert len(actual) > 2

        request_handler.delete_application(runtimes[1]["RT"], result['application_id'])

    @pytest.mark.slow
    def testPositive_Migration_When_Denied(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user4", "password": "pass4"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this (all of them should have migrated to runtimes[2]["RT"])
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['correctly_signed:src'] in actors[2]
        assert result['actor_map']['correctly_signed:sum'] in actors[2]
        assert result['actor_map']['correctly_signed:snk'] in actors[2]

        actual = request_handler.report(runtimes[2]["RT"], result['actor_map']['correctly_signed:snk'])
        assert len(actual) > 2

        request_handler.delete_application(runtimes[1]["RT"], result['application_id'])

###################################
#   Control interface authorization 
#   as well as user db management
###################################

    @pytest.mark.slow
    def testNegative_Control_Interface_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user6", "password": "pass6"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "correctly_signed", content['file'],
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app correctly_signed, did not fail for security reasons")

    @pytest.mark.slow
    def testPositive_Add_User(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        users_db=None
        try:
            request_handler.set_credentials({"user": "user0", "password": "pass0"})
            users_db = request_handler.get_users_db(runtimes[0]["RT"])
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        if users_db:
            #TODO: seem more efficient to have a dictionary instead of a list of users
            users_db['user7']={ "username": "user7",
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
            result = request_handler.post_users_db(runtimes[0]["RT"], users_db)
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        #Read the users database back again and check if Greta has been added
        try:
            users_db2 = request_handler.get_users_db(runtimes[0]["RT"])
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
    def testNegative_UnallowedUser(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user_not_allowed", "password": "pass1"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app correctly_signed did not fail for security reasons")  

    @pytest.mark.slow
    def testNegative_IncorrectPassword(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "incorrect_password"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app correctly_signed, did not fail for security reasons")  

    @pytest.mark.slow
    def testPositive_Local_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = request_handler.deploy_application(runtimes[0]["RT"], "correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 0.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['correctly_signed:src'] in actors[0]
        assert result['actor_map']['correctly_signed:sum'] in actors[0]
        assert result['actor_map']['correctly_signed:snk'] in actors[0]

        time.sleep(0.1)
        actual = request_handler.report(runtimes[0]["RT"], result['actor_map']['correctly_signed:snk'])
        assert len(actual) > 2

        request_handler.delete_application(runtimes[0]["RT"], result['application_id']) 

    @pytest.mark.slow
    def testPositive_External_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 5.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['correctly_signed:src'] in actors[1]
        assert result['actor_map']['correctly_signed:sum'] in actors[1]
        assert result['actor_map']['correctly_signed:snk'] in actors[1]

        time.sleep(0.1)
        actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['correctly_signed:snk'])
        assert len(actual) > 2

        request_handler.delete_application(runtimes[1]["RT"], result['application_id']) 

#    @pytest.mark.xfail
#    @pytest.mark.slow
#    def testPositive_RADIUS_Authentication(self):
#        _log.analyze("TESTRUN", "+", {})
#        global rt
#        global request_handler
#        global security_testdir
#        result = {}
#        try:
#            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
#            if not content:
#                raise Exception("Failed finding script, signature and cert, stopping here")
#            request_handler.set_credentials({"user": "user5", "password": "pass5"})
#            result = request_handler.deploy_application(runtimes[3]["RT"], "correctly_signed", content['file'], 
#                        content=content,
#                        check=True)
#        except Exception as e:
#            if isinstance(e, Timeout):
#                raise Exception("Can't connect to RADIUS server. Have you started a RADIUS server?")
#            elif e.message.startswith("401"):
#                raise Exception("Failed security verification of app correctly_signed")
#            _log.exception("Test deploy failed")
#            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")
#
#        # Verify that actors exist like this
#        try:
#            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
#        except Exception as err:
#            _log.error("Failed to get actors from runtimes, err={}".format(err))
#            raise
#        actors = fetch_and_log_runtime_actors()
#        assert result['actor_map']['correctly_signed:src'] in actors[3]
#        assert result['actor_map']['correctly_signed:sum'] in actors[3]
#        assert result['actor_map']['correctly_signed:snk'] in actors[3]
#
#        actual = request_handler.report(runtimes[3]["RT"], result['actor_map']['correctly_signed:snk'])
#        assert len(actual) > 2
#
#        request_handler.delete_application(runtimes[3]["RT"], result['application_id'])
