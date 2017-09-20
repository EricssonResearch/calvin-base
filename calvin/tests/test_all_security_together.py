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
from functools import partial
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
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="test_security_domain"
org_name='org.testexample'
orig_identity_provider_path = os.path.join(security_testdir,"identity_provider")
identity_provider_path = os.path.join(credentials_testdir, "identity_provider")
policy_storage_path = os.path.join(security_testdir, "policies")
actor_store_path = ""
application_store_path = ""

NBR_OF_RUNTIMES=3

import socket
# If this fails add hostname to the /etc/hosts file for 127.0.0.1
try:
    ip_addr = socket.gethostbyname(socket.gethostname())
    hostname = socket.gethostname()
    skip = False
except:
    skip = True

rt=[]
rt_attributes=[]
request_handler=None
storage_verified=False

@pytest.mark.slow
@pytest.mark.essential
@pytest.mark.skipif(skip, reason="Test all security could not resolve hostname, you might need to edit /etc/hosts")
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        import fileinput
        global rt
        global rt_attributes
        global request_handler
        global actor_store_path
        global application_store_path
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
        actor_store_path, application_store_path = helpers.sign_files_for_security_tests(credentials_testdir)
        runtimes = helpers.create_CA(domain_name, credentials_testdir, NBR_OF_RUNTIMES)

        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)
        #Let's use the admin user0 for request_handler 
        request_handler.set_credentials({"user": "user0", "password": "pass0"})

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])
#        rt_conf.set('global', 'storage_type', "securedht")

        # Runtime 0: Certificate authority, authentication server, authorization server.
        rt0_conf = copy.deepcopy(rt_conf)
        rt0_conf.set('global','storage_type','local')
        rt0_conf.set('security','certificate_authority',{
                        'domain_name':domain_name,
                        'is_ca':'True'
                    })
        rt0_conf.set("security", "security_conf", {
                        "comment": "Authorization-,Authentication service accepting external requests",
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
        helpers.start_runtime0(runtimes, rt, hostname, request_handler, tls=True)
        helpers.get_enrollment_passwords(runtimes, method="controlapi_set", rt=rt, request_handler=request_handler)
        # Other runtimes: external authentication, external authorization.
        rt_conf.set('global','storage_type','proxy')
        rt_conf.set('global','storage_proxy',"calvinip://%s:5000" % hostname )
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
                            'enrollment_password':runtimes[i]["enrollment_password"]
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

        helpers.start_other_runtimes(runtimes, rt, hostname, request_handler, tls=True)
        request.addfinalizer(self.teardown)


    def teardown(self):
        helpers.teardown_slow(rt, request_handler, hostname)


###################################
#   Signature related tests
###################################

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_CorrectlySignedApp_CorrectlySignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application(request_handler, rt[1], "correctly_signed", content) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[1], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[1], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[1], result['application_id']) 


    @pytest.mark.slow
    @pytest.mark.essential
    def testNegative_IncorrectlySignedApp(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "incorrectly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler, rt[1], "incorrectly_signed", content) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
        return

    @pytest.mark.slow
    @pytest.mark.essential
    def testNegative_CorrectlySignedApp_IncorrectlySignedActor(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctlySignedApp_incorrectlySignedActor.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application(request_handler, rt[1], "correctlySignedApp_incorrectlySignedActor", content) 
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctlySignedApp_incorrectlySignedActor")
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Failed deployment of app correctlySignedApp_incorrectlySignedActor, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctlySignedApp_incorrectlySignedActor:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[1], snk, kwargs={'active': True})
        try:
            helpers.actual_tokens(request_handler, rt[1], snk, size=5, retries=2)
        except Exception as e:
            if e.message.startswith("Not enough tokens"):
                # We were blocked, as we should
                helpers.delete_app(request_handler, rt[1], result['application_id']) 
                return
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
        raise Exception("Incorrectly signed actor was not stopped as it should have been")




###################################
#   Policy related tests
###################################

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_Permit_UnsignedApp_SignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = helpers.deploy_signed_application(request_handler, rt[1], "unsignedApp_signedActors", content) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_signedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[1], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[1], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[1], result['application_id']) 

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_Permit_UnsignedApp_UnsignedActor(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_unsignedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user3", "password": "pass3"})
            result = helpers.deploy_signed_application(request_handler, rt[1], "unsignedApp_unsignedActors", content) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_unsignedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_unsignedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[1], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[1], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[1], result['application_id']) 

    @pytest.mark.slow
    @pytest.mark.essential
    def testNegative_Deny_SignedApp_SignedActor_UnallowedRequirement(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application(request_handler, rt[2], "correctly_signed", content) 
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")


        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[2], snk, kwargs={'active': True})
        try:
            helpers.actual_tokens(request_handler, rt[2], snk, size=5, retries=2)
        except Exception as e:
            if e.message.startswith("Not enough tokens"):
                # We were blocked, as we should
                helpers.delete_app(request_handler, rt[2], result['application_id']) 
                return
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
        raise Exception("Actor with unallowed requirements was not stopped as it should have been")


    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_Local_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = helpers.deploy_signed_application(request_handler, rt[0], "unsignedApp_signedActors", content) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_signedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[0], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[0], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[0], result['application_id']) 

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_External_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = helpers.deploy_signed_application(request_handler, rt[1], "unsignedApp_signedActors", content) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_signedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[1], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[1], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[1], result['application_id']) 

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_Migration_When_Denied(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user4", "password": "pass4"})
            result = helpers.deploy_signed_application(request_handler, rt[1], "correctly_signed", content) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        # Verify that actors exist like this (all of them should have migrated to rt[2])
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['correctly_signed:src'] in actors[2]
        assert result['actor_map']['correctly_signed:sum'] in actors[2]
        assert result['actor_map']['correctly_signed:snk'] in actors[2]

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[2], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[2], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[1], result['application_id']) 

###################################
#   Control interface authorization 
#   as well as user db management
###################################

    @pytest.mark.slow
    @pytest.mark.essential
    def testNegative_Control_Interface_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user6", "password": "pass6"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler, rt[1], "correctly_signed", content) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Deployment of app correctly_signed, did not fail for security reasons")
        return

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_Add_User(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        users_db=None
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        users_db = helpers.retry(10, partial(request_handler.get_users_db, rt[0]), lambda _: True, "Failed to get users database")
        if users_db:
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
        helpers.retry(10, partial(request_handler.post_users_db, rt[0], users_db), lambda _: True, "Failed to post users database")
        #Read the users database back again and check if Greta has been added
        users_db2 = helpers.retry(10, partial(request_handler.get_users_db, rt[0]), lambda _: True, "Failed to get users database")
        if not 'user7' in users_db2:
            raise Exception("Failed to update the users_db")


###################################
#   Authentication related tests
###################################

    @pytest.mark.slow
    @pytest.mark.essential
    def testNegative_UnallowedUser(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user_not_allowed", "password": "pass1"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler, rt[1], "correctly_signed", content) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Deployment of app correctly_signed did not fail for security reasons")
        return

    @pytest.mark.slow
    @pytest.mark.essential
    def testNegative_IncorrectPassword(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "incorrect_password"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler, rt[1], "incorrectly_signed", content) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Deployment of app correctly_signed, did not fail for security reasons")  
        return

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_Local_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = helpers.deploy_signed_application(request_handler, rt[0], "correctly_signed", content) 
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 0.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[0], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[0], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[0], result['application_id']) 

    @pytest.mark.slow
    @pytest.mark.essential
    def testPositive_External_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        global storage_verified
        if not storage_verified:
            try:
                storage_verified = helpers.security_verify_storage(rt, request_handler)
            except Exception as err:
                _log.error("Failed storage verification, err={}".format(err))
                raise

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = helpers.deploy_signed_application(request_handler, rt[1], "correctly_signed", content) 
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 5.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(rt[1], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, rt[1], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, rt[1], result['application_id']) 

#    @pytest.mark.xfail
#    @pytest.mark.slow
#    def testPositive_RADIUS_Authentication(self):
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
#            content = Security.verify_signature_get_files(os.path.join(application_store_path, "correctly_signed.calvin"))
#            if not content:
#                raise Exception("Failed finding script, signature and cert, stopping here")
#            request_handler.set_credentials({"user": "user5", "password": "pass5"})
#            result = request_handler.deploy_application(rt[3], "correctly_signed", content['file'], 
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
#            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
#        except Exception as err:
#            _log.error("Failed to get actors from runtimes, err={}".format(err))
#            raise
#            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
#        assert result['actor_map']['correctly_signed:src'] in actors[3]
#        assert result['actor_map']['correctly_signed:sum'] in actors[3]
#        assert result['actor_map']['correctly_signed:snk'] in actors[3]
#
#        actual = request_handler.report(rt[3], result['actor_map']['correctly_signed:snk'])
#        assert len(actual) > 2
#
#        helpers.delete_app(request_handler, rt[3], result['application_id']) 

