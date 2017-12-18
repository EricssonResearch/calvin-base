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
from calvin.csparser import cscompile as compiler
from calvin.Tools import cscompiler as compile_tool
from calvin.Tools import deployer
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
credentials_testdir = os.path.join(homefolder, ".calvin","test_secure_calvin")
runtimesdir = os.path.join(credentials_testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="com.ericsson"
org_name='com.ericsson'
orig_identity_provider_path = os.path.join(security_testdir,"identity_provider")
identity_provider_path = os.path.join(credentials_testdir, "identity_provider")
policy_storage_path = os.path.join(security_testdir, "policies")
actor_store_path = ""
application_store_path = ""

USE_TLS=True
USE_AUTHZ=True
#NOTE, only proxy storage currently work, dynamically finding authz and auth
# servers fails for DHT and SecureDHT for some reason
PROXY_STORAGE = bool(int(os.environ.get("CALVIN_TESTING_PROXY_STORAGE", True)))
DHT = bool(int(os.environ.get("CALVIN_TESTING_DHT_STORAGE", False)))
SECURE_DHT = bool(int(os.environ.get("CALVIN_TESTING_SECURE_DHT_STORAGE", False)))

#A minimum of 4 runtimes is assumed
NBR_OF_RUNTIMES=5
rt1 = None
rt2 = None
rt3 = None

import socket
# If this fails add hostname to the /etc/hosts file for 127.0.0.1
try:
    ip_addr = socket.gethostbyname(socket.gethostname())
    hostname = socket.gethostname()
    skip = False
except:
    skip = True
    hostname=None

runtimes=[]
rt_attributes=[]
request_handler=None
storage_verified=False

def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)

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

def assert_lists_equal(expected, actual, min_length=5):
    assert len(actual) >= min_length
    assert actual
    assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True)

#
def wait_until_nbr(rt, actor_id, size=5, retries=20, sleep=0.1):
    for i in range(retries):
        r = request_handler.report(rt, actor_id)
        l = r if isinstance(r, numbers.Number) else len(r)
        if l >= size:
            break
        time.sleep(sleep)
    assert l >= size

def get_runtime(n=1):
    import random
    _runtimes = [runtimes[1]["RT"], runtimes[2]["RT"], runtimes[3]["RT"]]
    random.shuffle(_runtimes)
    return _runtimes[:n]

configured=False
def setup_persistant_data():
    from calvin.Tools.csruntime import csruntime
    from conftest import _config_pytest
    import fileinput
    global storage_verified
    global runtimes
    global rt_attributes
    global request_handler
    global actor_store_path
    global application_store_path
    global rt1
    global rt2
    global rt3
    global hostname
    global configured
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
    if USE_TLS:
        runtimes = helpers.create_CA(domain_name, credentials_testdir, NBR_OF_RUNTIMES)
        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)
    else:
        #CA does not listen to http (only https) for certificate requests, so we'll have to create them before starting test
        runtimes = helpers.create_CA_and_generate_runtime_certs(domain_name, credentials_testdir, NBR_OF_RUNTIMES)

        request_handler = RequestHandler()
    #Let's use the admin user0 for request_handler 
    request_handler.set_credentials({"user": "user0", "password": "pass0"})

    rt_conf = copy.deepcopy(_conf)
    if USE_TLS:
        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
        rt_conf.set('security', 'control_interface_security', "tls")
    rt_conf.set('security', 'security_dir', credentials_testdir)
    rt_conf.set('global', 'actor_paths', [actor_store_path])

    # Runtime 0: Certificate authority, authentication server, authorization server.
    rt0_conf = copy.deepcopy(rt_conf)
    if PROXY_STORAGE:
        rt0_conf.set('global','storage_type','local')
    elif SECURE_DHT:
        rt0_conf.set('global','storage_type','securedht')
    else:
        #Default storage is DHT
        rt0_conf.set('global','storage_type','dht')
    rt0_conf.set('security','certificate_authority',{
                    'domain_name':domain_name,
                    'is_ca':True
                })
    if USE_AUTHZ:
        rt0_conf.set("security", "security_conf", {
                        "comment": "Authorization-,Authentication service accepting external requests",
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
    if not USE_TLS or hostname==None:
        print "Don't user TLS or hostname none, hostname={}".format(hostname)
        hostname="localhost"
    helpers.start_runtime0(runtimes, hostname, request_handler, tls=USE_TLS)
    helpers.get_enrollment_passwords(runtimes, method="controlapi_set", request_handler=request_handler)
    # Other runtimes: external authentication, external authorization.
    if PROXY_STORAGE:
        rt_conf.set('global','storage_type','proxy')
        if USE_TLS:
            rt_conf.set('global','storage_proxy',"calvinip://%s:5000" % hostname )
        else:
            rt_conf.set('global','storage_proxy',"calvinip://localhost:5000" )
        if USE_AUTHZ:
            rt_conf.set("security", "security_conf", {
                            "comment": "External authentication, external authorization",
                            "authentication": {
                                "procedure": "external"
                            },
                            "authorization": {
                                "procedure": "external"
                            }
                        })
    elif DHT:
        rt_conf.set('global','storage_type','dht')
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
    else:
        rt_conf.set('global','storage_type','securedht')
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
        rt_conf.set('security','certificate_authority',{
                        'domain_name':domain_name,
                        'is_ca':False,
                        'ca_control_uri':"https://%s:5020" % hostname,
                        'enrollment_password':runtimes[i]["enrollment_password"]
                    })
        rt_conf.save("/tmp/calvin500{}.conf".format(i))

    configured=True

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
    helpers.start_other_runtimes(runtimes, hostname, request_handler, tls=USE_TLS)
    rt1=runtimes[1]["RT"]
    rt2=runtimes[2]["RT"]
    rt3=runtimes[3]["RT"]
    for i in range(1, NBR_OF_RUNTIMES):
        try:
            runtimes[i]["RT"].id = request_handler.get_node_id(runtimes[i]["RT"])
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime.\n\te={}".format(e))
            _log.exception("Test deploy failed")
            raise Exception("Failed to get node id, e={}".format(e))

@pytest.mark.slow
@pytest.mark.skipif(skip, reason="Test all security could not resolve hostname, you might need to edit /etc/hosts")
class CalvinSecureTestBase(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="module")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        import fileinput
        global storage_verified
        global runtimes
        global rt_attributes
        global request_handler
        global actor_store_path
        global application_store_path
        global rt1
        global rt2
        global rt3
        global hostname

        if not configured:
            setup_persistant_data()

        request.addfinalizer(self.teardown)

    def teardown(self):
        helpers.teardown_slow(runtimes, request_handler, hostname)

    def assert_lists_equal(self, expected, actual, min_length=5):
        self.assertTrue(len(actual) >= min_length, "Received data too short (%d), need at least %d" % (len(actual), min_length))
        self._assert_lists_equal(expected, actual)

    def _assert_lists_equal(self, expected, actual):
        assert actual
        assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True)

    def get_port_property(self, app_info, actor, port, direction, key):
        """Access port properties in a robust way since order might change between parser revisions"""
        # Get list of port properties
        props = app_info['port_properties'][actor]
        for p in props:
            found = p['direction'] == direction and p['port'] == port
            if not found:
                continue
            return p['properties'][key]
        raise KeyError("Property '{}' not present.".format(key))

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


###################################
#   Signature related tests
###################################
@pytest.mark.skipif(USE_AUTHZ!=True, reason="Makes no sense without authorization enabled")
@pytest.mark.slow
@pytest.mark.essential
class TestSignedCode(CalvinSecureTestBase):

    def testPositive_CorrectlySignedApp_CorrectlySignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[1]["RT"],
                                                       "correctly_signed",
                                                       os.path.join(application_store_path, "correctly_signed.calvin")) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.error("Test deploy failed, err={}".format(e))
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[1]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[1]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 

#    def testPositive_CorrectlySignedAppInfo_CorrectlySignedActors(self):
#        _log.analyze("TESTRUN", "+", {})
#        result = {}
#
#        script = """
#          src : std.CountTimer()
#          snk : test.Sink(store_tokens=1, quiet=1)
#          src.integer > snk.token
#        """
#
#        app_info, errors, warnings = self.compile_script(script, "simple")
#        d = deployer.Deployer(rt, app_info, request_handler=request_handler)
#        deploy_app(d)
#        try:
#            request_handler.set_credentials({"user": "user1", "password": "pass1"})
#            result = helpers.deploy_signed_application(request_handler, runtimes[1]["RT"],
#                                                       "correctly_signed",
#                                                       os.path.join(application_store_path, "correctly_signed.calvin")) 
#        except Exception as e:
#            if e.message.startswith("401"):
#                raise Exception("Failed security verification of app correctly_signed")
#            _log.error("Test deploy failed, err={}".format(e))
#            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")
#
#        snk = result['actor_map']['correctly_signed:snk']
#        request_handler.set_credentials({"user": "user0", "password": "pass0"})
#        request_handler.report(runtimes[1]["RT"], snk, kwargs={'active': True})
#        actual = helpers.actual_tokens(request_handler, runtimes[1]["RT"], snk, size=5, retries=20)
#        assert len(actual) > 4
#
#        helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 


    def testNegative_IncorrectlySignedApp(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler, runtimes[1]["RT"],
                                                                        "incorrectly_signed",
                                                                        os.path.join(application_store_path, "incorrectly_signed.calvin")) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
        return

    def testNegative_CorrectlySignedApp_IncorrectlySignedActor(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[1]["RT"],
                                                       "correctlySignedApp_incorrectlySignedActor",
                                                       os.path.join(application_store_path, "correctlySignedApp_incorrectlySignedActor.calvin")) 
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctlySignedApp_incorrectlySignedActor")
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Failed deployment of app correctlySignedApp_incorrectlySignedActor, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctlySignedApp_incorrectlySignedActor:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[1]["RT"], snk, kwargs={'active': True})
        try:
            helpers.actual_tokens(request_handler, runtimes[1]["RT"], snk, size=5, retries=2)
        except Exception as e:
            if e.message.startswith("Not enough tokens"):
                # We were blocked, as we should
                helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 
                return
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
        raise Exception("Incorrectly signed actor was not stopped as it should have been")




###################################
#   Policy related tests
###################################
@pytest.mark.skipif(USE_AUTHZ!=True, reason="Makes no sense without authorization enabled")
@pytest.mark.slow
@pytest.mark.essential
class TestAuthorization(CalvinSecureTestBase):
    def testPositive_Permit_UnsignedApp_SignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[1]["RT"],
                                                       "unsignedApp_signedActors",
                                                       os.path.join(application_store_path, "unsignedApp_signedActors.calvin")) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_signedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[1]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[1]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 

    def testPositive_Permit_UnsignedApp_UnsignedActor(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token

      rule simple: node_attr_match(index=["node_name", {"organization": "com.ericsson"}])
      apply src, snk: simple
        """
        try:
            request_handler.set_credentials({"user": "user3", "password": "pass3"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[1]["RT"],
                                                       "unsignedApp_unsignedActors", 
                                                       os.path.join(application_store_path, "unsignedApp_unsignedActors.calvin")) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_unsignedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_unsignedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[1]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[1]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 

    def testNegative_Deny_SignedApp_SignedActor_UnallowedRequirement(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[2]["RT"],
                                                       "correctly_signed",
                                                       os.path.join(application_store_path, "correctly_signed.calvin")) 
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")


        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[2]["RT"], snk, kwargs={'active': True})
        try:
            helpers.actual_tokens(request_handler, runtimes[2]["RT"], snk, size=5, retries=2)
        except Exception as e:
            if e.message.startswith("Not enough tokens"):
                # We were blocked, as we should
                helpers.delete_app(request_handler, runtimes[2]["RT"], result['application_id']) 
                return
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
        raise Exception("Actor with unallowed requirements was not stopped as it should have been")


    def testPositive_Local_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[0]["RT"],
                                                       "unsignedApp_signedActors",
                                                       os.path.join(application_store_path, "unsignedApp_signedActors.calvin")) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_signedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[0]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[0]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[0]["RT"], result['application_id']) 

    def testPositive_External_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[1]["RT"],
                                                       "unsignedApp_signedActors",
                                                       os.path.join(application_store_path, "unsignedApp_signedActors.calvin")) 
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_signedActors, no use to verify if requirements fulfilled")

        snk = result['actor_map']['unsignedApp_signedActors:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[1]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[1]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 

    def testPositive_Migration_When_Denied(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user4", "password": "pass4"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[1]["RT"],
                                                       "correctly_signed",
                                                       os.path.join(application_store_path, "correctly_signed.calvin")) 
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

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[2]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[2]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 

###################################
#   Control interface authorization 
#   as well as user db management
###################################
@pytest.mark.skipif(USE_AUTHZ!=True, reason="Makes no sense without authorization enabled")
@pytest.mark.slow
@pytest.mark.essential
class TestControlInterfaceAuthorization(CalvinSecureTestBase):
    def testNegative_Control_Interface_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user6", "password": "pass6"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler,
                                                                        runtimes[1]["RT"],
                                                                        "correctly_signed",
                                                                        os.path.join(application_store_path, "correctly_signed.calvin")) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Deployment of app correctly_signed, did not fail for security reasons")
        return

    def testPositive_Add_User(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        users_db=None
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        users_db = helpers.retry(10, partial(request_handler.get_users_db, runtimes[0]["RT"]), lambda _: True, "Failed to get users database")
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
        helpers.retry(10, partial(request_handler.post_users_db, runtimes[0]["RT"], users_db), lambda _: True, "Failed to post users database")
        #Read the users database back again and check if Greta has been added
        users_db2 = helpers.retry(10, partial(request_handler.get_users_db, runtimes[0]["RT"]), lambda _: True, "Failed to get users database")
        if not 'user7' in users_db2:
            raise Exception("Failed to update the users_db")


###################################
#   Authentication related tests
###################################
@pytest.mark.slow
@pytest.mark.essential
class TestAuthentication(CalvinSecureTestBase):
    def testNegative_UnallowedUser(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user_not_allowed", "password": "pass1"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler,
                                                                        runtimes[1]["RT"],
                                                                        "correctly_signed",
                                                                        os.path.join(application_store_path, "correctly_signed.calvin")) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Deployment of app correctly_signed did not fail for security reasons")
        return

    def testNegative_IncorrectPassword(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user1", "password": "incorrect_password"})
            result = helpers.deploy_signed_application_that_should_fail(request_handler,
                                                                        runtimes[1]["RT"],
                                                                        "incorrectly_signed",
                                                                        os.path.join(application_store_path, "correctly_signed.calvin")) 
        except Exception as e:
            _log.error("Test deploy failed for non security reasons, e={}".format(e))
            raise Exception("Deployment of app correctly_signed, did not fail for security reasons")  
        return

    def testPositive_Local_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[0]["RT"],
                                                       "correctly_signed",
                                                       os.path.join(application_store_path, "correctly_signed.calvin")) 
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 0.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[0]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[0]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[0]["RT"], result['application_id']) 

    def testPositive_External_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = helpers.deploy_signed_application(request_handler,
                                                       runtimes[1]["RT"],
                                                       "correctly_signed",
                                                       os.path.join(application_store_path, "correctly_signed.calvin")) 
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app correctly_signed, no use to verify if requirements fulfilled")

        snk = result['actor_map']['correctly_signed:snk']
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        request_handler.report(runtimes[1]["RT"], snk, kwargs={'active': True})
        actual = helpers.actual_tokens(request_handler, runtimes[1]["RT"], snk, size=5, retries=20)
        assert len(actual) > 4

        helpers.delete_app(request_handler, runtimes[1]["RT"], result['application_id']) 

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
#            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
#        except Exception as err:
#            _log.error("Failed to get actors from runtimes, err={}".format(err))
#            raise
#            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
#        assert result['actor_map']['correctly_signed:src'] in actors[3]
#        assert result['actor_map']['correctly_signed:sum'] in actors[3]
#        assert result['actor_map']['correctly_signed:snk'] in actors[3]
#
#        actual = request_handler.report(runtimes[3]["RT"], result['actor_map']['correctly_signed:snk'])
#        assert len(actual) > 2
#
#        helpers.delete_app(request_handler, runtimes[3]["RT"], result['application_id']) 




###################################
#   Non-security Calvin tests
###################################
@pytest.mark.slow
#@pytest.mark.essential
class TestNodeSetup(CalvinSecureTestBase):

    """Testing starting a node"""

    def testStartNode(self):
        """Testing starting node"""
        #import sys
        #from twisted.python import log
        #from twisted.internet import defer
        #log.startLogging(sys.stdout)
        #defer.setDebugging(True)

        assert request_handler.get_node(rt1, rt1.id)['uris'] == rt1.uris


#@pytest.mark.essential
@pytest.mark.slow
class TestRemoteConnection(CalvinSecureTestBase):


    """Testing remote connections"""

    def testRemoteOneActor(self):
        """Testing remote port"""
        from twisted.python import log
        from twisted.internet import defer
        import sys
        defer.setDebugging(True)
        log.startLogging(sys.stdout)

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')
        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', rt.id, src, 'integer')

        # Wait for some tokens
        actual = wait_for_tokens(rt, snk, 10)

        request_handler.disconnect(rt, src)

        # Fetch sent
        expected = expected_tokens(rt, src, 'sum')

        assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testRemoteSlowPort(self):
        """Testing remote slow port and that token flow control works"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        snk1 = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'flow.Alternate2', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.01, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)
        time.sleep(1)
        request_handler.connect(rt, snk1, 'token', peer.id, alt, 'token')
        request_handler.connect(peer, alt, 'token_1', rt.id, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', rt.id, src2, 'integer')

        actual = wait_for_tokens(rt, snk1, 10)

        request_handler.disconnect(rt, src1)
        request_handler.disconnect(rt, src2)

        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))

        assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk1)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

    @pytest.mark.xfail
    def testRemoteSlowFanoutPort(self):
        """Testing remote slow port with fan out and that token flow control works"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        snk1 = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(peer, 'test.Sink', 'snk2', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'flow.Alternate2', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        request_handler.connect(rt, snk1, 'token', peer.id, alt, 'token')
        request_handler.connect(peer, snk2, 'token', rt.id, src1, 'integer')
        request_handler.connect(peer, alt, 'token_1', rt.id, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', rt.id, src2, 'integer')

        # Wait for some tokens
        actual_1 = wait_for_tokens(rt, snk1, 10)
        actual_2 = wait_for_tokens(peer, snk2, 10)

        request_handler.disconnect(rt, src1)
        request_handler.disconnect(rt, src2)

        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))

        assert_lists_equal(expected, actual_1)
        assert_lists_equal(expected_1, actual_2)

        request_handler.delete_actor(rt, snk1)
        request_handler.delete_actor(peer, snk2)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

#@pytest.mark.essential
@pytest.mark.slow
class TestActorMigration(CalvinSecureTestBase):

    def testOutPortRemoteToLocalMigration(self):
        """Testing outport remote to local migration"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]


        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', rt.id, src, 'integer')

        actual_1 = wait_for_tokens(rt, snk)

        self.migrate(rt, peer, src)

        # Wait for at least queue + 1 tokens
        wait_for_tokens(rt, snk, len(actual_1)+5)
        expected = expected_tokens(peer, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))

        assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(peer, src)

    def testFanOutPortLocalToRemoteMigration(self):
        """Testing outport with fan-out local to remote migration"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        src = request_handler.new_actor_wargs(rt, "std.CountTimer", "src", sleep=0.1, steps=100)
        snk_1 = request_handler.new_actor_wargs(rt, "test.Sink", "snk-1", store_tokens=1, quiet=1)
        snk_2 = request_handler.new_actor_wargs(rt, "test.Sink", "snk-2", store_tokens=1, quiet=1)

        request_handler.set_port_property(rt, src, 'out', 'integer',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(rt, snk_1, 'token', rt.id, src, 'integer')
        request_handler.connect(rt, snk_2, 'token', rt.id, src, 'integer')
        wait_for_tokens(rt, snk_1)
        wait_for_tokens(rt, snk_2)

        expected = expected_tokens(rt, src, 'seq')
        actual_1 = actual_tokens(rt, snk_1, len(expected))
        self.assert_lists_equal(expected, actual_1)

        expected = expected_tokens(rt, src, 'seq')
        actual_2 = actual_tokens(rt, snk_2, len(expected))

        self.assert_lists_equal(expected, actual_2)

        self.migrate(rt, peer, src)

        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(rt, snk_1, len(actual_1)+5)

        expected = expected_tokens(peer, src, 'seq')
        actual = actual_tokens(rt, snk_1, len(expected))
        self.assert_lists_equal(expected, actual)

        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(rt, snk_2, len(actual_2)+5)
        expected = expected_tokens(peer, src, 'seq')
        actual = actual_tokens(rt, snk_2, len(expected))
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(peer, src)
        request_handler.delete_actor(rt, snk_1)
        request_handler.delete_actor(rt, snk_2)

    def testOutPortLocalToRemoteMigration(self):
        """Testing outport local to remote migration"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', peer.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = actual_tokens(rt, snk)
        self.migrate(peer, rt, src)

        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and back repeatedly"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', peer.id, src, 'integer')

        wait_for_tokens(rt, snk)

        actual_x = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                self.migrate(peer, rt, src)
            else:
                self.migrate(rt, peer, src)
            actual_x = actual_tokens(rt, snk, len(actual_x)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testInOutPortRemoteToLocalMigration(self):
        """Testing out- and inport remote to local migration"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', rt.id, src, 'integer')
        actual_1 = wait_for_tokens(rt, snk)

        self.migrate(peer, rt, csum)

        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(rt, csum)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and revers repeatedly"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', rt.id, csum, 'integer')
        request_handler.connect(rt, csum, 'integer', rt.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_x = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                self.migrate(rt, peer, csum)
            else:
                self.migrate(peer, rt, csum)
            actual_x = actual_tokens(rt, snk, len(actual_x)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalToRemoteMigration(self):
        """Testing out- and inport local to remote migration"""

        rt = runtimes[1]["RT"]
        peer = runtimes[2]["RT"]

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', rt.id, csum, 'integer')
        request_handler.connect(rt, csum, 'integer', rt.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = wait_for_tokens(rt, snk)
        self.migrate(rt, peer, csum)
        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)


    def testInOutPortRemoteToRemoteMigration(self):
        """Testing out- and inport remote to remote migration"""
        rt = runtimes[1]["RT"]
        peer0 = runtimes[2]["RT"]
        peer1 = runtimes[3]["RT"]

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer0, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer0.id, csum, 'integer')
        request_handler.connect(peer0, csum, 'integer', rt.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = actual_tokens(rt, snk)
        self.migrate(peer0, peer1, csum)
        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer1, csum)
        request_handler.delete_actor(rt, src)

    def testExplicitStateMigration(self):
        """Testing migration of explicit state handling"""

        rt = runtimes[1]["RT"]
        peer0 = runtimes[2]["RT"]

        snk = request_handler.new_actor_wargs(peer0, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        wrapper = request_handler.new_actor(rt, 'misc.ExplicitStateExample', 'wrapper')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(peer0, snk, 'token', rt.id, wrapper, 'token')
        request_handler.connect(rt, wrapper, 'token', rt.id, src, 'integer')

        actual_1 = wait_for_tokens(peer0, snk)

        self.migrate(rt, peer0, wrapper)
        wait_for_tokens(peer0, snk, len(actual_1)+5)

        expected = [u'((( 1 )))', u'((( 2 )))', u'((( 3 )))', u'((( 4 )))', u'((( 5 )))', u'((( 6 )))', u'((( 7 )))', u'((( 8 )))']
        actual = actual_tokens(peer0, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        request_handler.delete_actor(peer0, snk)
        request_handler.delete_actor(peer0, wrapper)
        request_handler.delete_actor(rt, src)

#@pytest.mark.essential
@pytest.mark.slow
class TestCalvinScript(CalvinSecureTestBase):

    def testCompileSimple(self):
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token
    """

        rt = runtimes[1]["RT"]
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info, request_handler=request_handler)
        deploy_app(d)

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        wait_for_tokens(rt, snk)
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))
        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testDestroyAppWithLocalActors(self):
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token
    """

        rt = runtimes[1]["RT"]
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info, request_handler=request_handler)

        deploy_app(d)
        app_id = d.app_id

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        applications = request_handler.get_applications(rt)
        assert app_id in applications

        helpers.destroy_app(d)

        applications = request_handler.get_applications(rt)
        assert app_id not in applications

        actors = request_handler.get_actors(rt)
        assert src not in actors
        assert snk not in actors

    def testDestroyAppWithMigratedActors(self):
        rt, rt1, rt2 = get_runtime(3)

        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token"""

        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info, request_handler=request_handler)
        deploy_app(d)
        app_id = d.app_id

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        self.migrate(rt, rt1, snk)
        self.migrate(rt, rt2, src)

        applications = request_handler.get_applications(rt)
        assert app_id in applications

        helpers.destroy_app(d)

        applications = request_handler.get_applications(rt)
        assert app_id not in applications

        for retry in range(1, 5):
            actors = []
            actors.extend(request_handler.get_actors(rt))
            actors.extend(request_handler.get_actors(rt1))
            actors.extend(request_handler.get_actors(rt2))
            intersection = [a for a in actors if a in d.actor_map.values()]
            if len(intersection) > 0:
                print("Not all actors removed, checking in %s" % (retry, ))
                time.sleep(retry)
            else:
                break

        for actor in d.actor_map.values():
            assert actor not in actors

#@pytest.mark.essential
class TestConnections(CalvinSecureTestBase):
    @pytest.mark.slow
    def testLocalSourceSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, snk, 'token', rt1.id, src, 'integer')

        actual = wait_for_tokens(rt1, snk)
        expected = expected_tokens(rt1, src, 'seq')

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt1, snk)

    def testMigrateSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, snk, 'token', rt1.id, src, 'integer')

        pre_migrate = wait_for_tokens(rt1, snk)

        self.migrate(rt1, rt2, snk)

        actual = wait_for_tokens(rt2, snk, len(pre_migrate)+5)
        expected = expected_tokens(rt1, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt2, snk)

    def testMigrateSource(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, snk, 'token', rt1.id, src, 'integer')

        actual = wait_for_tokens(rt1, snk)

        self.migrate(rt1, rt2, src)

        actual = actual_tokens(rt1, snk, len(actual)+5 )
        expected = expected_tokens(rt2, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt2, src)
        request_handler.delete_actor(rt1, snk)

    def testTwoStepMigrateSinkSource(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, snk, 'token', rt1.id, src, 'integer')

        pre_migrate = wait_for_tokens(rt1, snk)
        self.migrate(rt1, rt2, snk)
        mid_migrate = wait_for_tokens(rt2, snk, len(pre_migrate)+5)
        self.migrate(rt1, rt2, src)
        post_migrate = wait_for_tokens(rt2, snk, len(mid_migrate)+5)

        expected = expected_tokens(rt2, src)

        self.assert_lists_equal(expected, post_migrate, min_length=10)
        request_handler.delete_actor(rt2, src)
        request_handler.delete_actor(rt2, snk)

    def testTwoStepMigrateSourceSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, snk, 'token', rt1.id, src, 'integer')

        pre_migrate = wait_for_tokens(rt1, snk)
        self.migrate(rt1, rt2, src)
        mid_migrate = wait_for_tokens(rt1, snk, len(pre_migrate)+5)
        self.migrate(rt1, rt2, snk)
        post_migrate = wait_for_tokens(rt2, snk, len(mid_migrate)+5)

        expected = expected_tokens(rt2, src)
        self.assert_lists_equal(expected, post_migrate, min_length=15)

        request_handler.delete_actor(rt2, src)
        request_handler.delete_actor(rt2, snk)

#@pytest.mark.essential
class TestScripts(CalvinSecureTestBase):

    @pytest.mark.slow
    def testInlineScript(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : test.Sink(store_tokens=1, quiet=1)
          src.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['simple:snk']
        src = d.actor_map['simple:src']

        actual = wait_for_tokens(rt1, snk)
        expected = expected_tokens(rt1, src)

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

    @pytest.mark.slow
    def testFileScript(self):
        _log.analyze("TESTRUN", "+", {})
        scriptname = 'test1'
        scriptfile = absolute_filename("scripts/%s.calvin" % (scriptname, ))
        app_info, issuetracker = compile_tool.compile_file(scriptfile, ds=False, ir=False)
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        src = d.actor_map['%s:src' % scriptname]
        snk = d.actor_map['%s:snk' % scriptname]

        actual = wait_for_tokens(rt1, snk)
        expected = expected_tokens(rt1, src)

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

class TestStateMigration(CalvinSecureTestBase):

    def testSimpleState(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : test.Sink(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        tokens = len(wait_for_tokens(rt1, snk))
        self.migrate(rt1, rt2, csum)

        actual = actual_tokens(rt1, snk, tokens+5)
        expected = expected_tokens(rt1, src, 'sum')

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

@pytest.mark.slow
#@pytest.mark.essential
class TestAppLifeCycle(CalvinSecureTestBase):

    def testAppDestructionOneRemote(self):
        from functools import partial

        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : test.Sink(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        tokens = len(wait_for_tokens(rt1, snk))
        self.migrate(rt1, rt2, csum)

        actual = actual_tokens(rt1, snk, tokens+5)
        expected = expected_tokens(rt1, src, 'sum')

        self.assert_lists_equal(expected, actual)

        helpers.delete_app(request_handler, rt1, d.app_id)

        def check_actors_gone(runtime):
            for actor in src, csum, snk:
                try:
                    a = request_handler.get_actor(runtime, actor)
                    if a is not None:
                        _log.info("Actor '%r' still present on runtime '%r" % (actor, runtime.id, ))
                        return False
                except:
                    pass
            return True

        for rt in [ rt1, rt2, rt3 ]:
            check_rt = partial(check_actors_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Not all actors gone on rt '%r'" % (rt.id, ))
            assert all_gone

        def check_application_gone(runtime):
            try :
                app = request_handler.get_application(runtime, d.app_id)
            except Exception as e:
                msg = str(e.message)
                if msg.startswith("404"):
                    return True
            return app is None

        for rt in [ rt1, rt2, rt3 ]:
            check_rt = partial(check_application_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Application still present on rt '%r'" % (rt.id, ))
            assert all_gone

    def testAppDestructionAllRemote(self):
        from functools import partial
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : test.Sink(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        #? import sys
        #? from twisted.python import log
        #? log.startLogging(sys.stdout)

        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        tokens = len(wait_for_tokens(rt1, snk))

        self.migrate(rt1, rt2, src)
        self.migrate(rt1, rt2, csum)
        self.migrate(rt1, rt2, snk)

        actual = actual_tokens(rt2, snk, tokens+5)
        expected = expected_tokens(rt2, src, 'sum')

        self.assert_lists_equal(expected, actual)

        helpers.delete_app(request_handler, rt1, d.app_id)

        def check_actors_gone(runtime):
            for actor in src, csum, snk:
                try:
                    a = request_handler.get_actor(runtime, actor)
                    if a is not None:
                        _log.info("Actor '%r' still present on runtime '%r" % (actor, runtime.id, ))
                        return False
                except:
                    pass
            return True

        for rt in [ rt1, rt2, rt3 ]:
            check_rt = partial(check_actors_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Not all actors gone on rt '%r'" % (rt.id, ))
            assert all_gone

        def check_application_gone(runtime):
            try :
                app = request_handler.get_application(runtime, d.app_id)
            except Exception as e:
                msg = str(e.message)
                if msg.startswith("404"):
                    return True
            return app is None

        for rt in [ rt1, rt2, rt3 ]:
            check_rt = partial(check_application_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Application still present on rt '%r'" % (rt.id, ))
            assert all_gone

#@pytest.mark.essential
class TestEnabledToEnabledBug(CalvinSecureTestBase):

    def test10(self):
        _log.analyze("TESTRUN", "+", {})
        # Two actors, doesn't seem to trigger the bug
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, snk, 'token', rt1.id, src, 'integer')

        actual = actual_tokens(rt1, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt1, snk)

    def test11(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test10, but scripted
        script = """
            src : std.Counter()
            snk : test.Sink(store_tokens=1, quiet=1)

            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['simple:snk']

        actual = actual_tokens(rt1, snk, 10)
        self.assert_lists_equal(range(1, 10), actual)

        helpers.destroy_app(d)

    def test20(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(rt1, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, snk, 'token', rt1.id, ity, 'token')
        request_handler.connect(rt1, ity, 'token', rt1.id, src, 'integer')

        actual = actual_tokens(rt1, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt1, ity)
        request_handler.delete_actor(rt1, snk)

    def test21(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(rt2, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(rt3, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt3, snk, 'token', rt2.id, ity, 'token')
        request_handler.connect(rt2, ity, 'token', rt1.id, src, 'integer')

        actual = actual_tokens(rt3, snk, 10)
        self.assert_lists_equal(range(1,10), actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt2, ity)
        request_handler.delete_actor(rt3, snk)

    def test22(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(rt2, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(rt3, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt2, ity, 'token', rt1.id, src, 'integer')
        request_handler.connect(rt3, snk, 'token', rt2.id, ity, 'token')

        actual = actual_tokens(rt3, snk, 10)
        self.assert_lists_equal(range(1,10), actual)

        actual = actual_tokens(rt3, snk, len(actual)+1)
        self.assert_lists_equal(range(1,len(actual)), actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt2, ity)
        request_handler.delete_actor(rt3, snk)

    def test25(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(rt1, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(rt1, ity, 'token', rt1.id, src, 'integer')
        request_handler.connect(rt1, snk, 'token', rt1.id, ity, 'token')

        actual = actual_tokens(rt1, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt1, ity)
        request_handler.delete_actor(rt1, snk)

    def test26(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test20
        script = """
            src : std.Counter()
            ity : std.Identity()
            snk : test.Sink(store_tokens=1, quiet=1)

            src.integer > ity.token
            ity.token > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)
        snk = d.actor_map['simple:snk']

        actual = actual_tokens(rt1, snk, 10)
        self.assert_lists_equal(range(1,10), actual)

        helpers.destroy_app(d)


    def test30(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(rt1, src, 'out', 'integer',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(rt1, snk1, 'token', rt1.id, src, 'integer')
        request_handler.connect(rt1, snk2, 'token', rt1.id, src, 'integer')

        actual1 = actual_tokens(rt1, snk1, 10)
        actual2 = actual_tokens(rt1, snk2, 10)

        self.assert_lists_equal(list(range(1, 10)), actual1)
        self.assert_lists_equal(list(range(1, 10)), actual2)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt1, snk1)
        request_handler.delete_actor(rt1, snk2)

    def test31(self):
        # Verify that fanout defined implicitly in scripts is handled correctly
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)

            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test31")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk1 = d.actor_map['test31:snk1']
        snk2 = d.actor_map['test31:snk2']
        actual1 = actual_tokens(rt1, snk1, 10)
        actual2 = actual_tokens(rt1, snk2, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)

        d.destroy()

    def test32(self):
        # Verify that fanout from component inports is handled correctly
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Foo() in -> a, b{
              a : std.Identity()
              b : std.Identity()
              .in >  a.token
              .in > b.token
              a.token > .a
              b.token > .b
            }

            snk2 : test.Sink(store_tokens=1, quiet=1)
            snk1 : test.Sink(store_tokens=1, quiet=1)
            foo : Foo()
            req : std.Counter()
            req.integer > foo.in
            foo.a > snk1.token
            foo.b > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test32")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk1 = d.actor_map['test32:snk1']
        snk2 = d.actor_map['test32:snk2']
        actual1 = actual_tokens(rt1, snk1, 10)
        actual2 = actual_tokens(rt1, snk2, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)

        d.destroy()

    def test40(self):
        # Verify round robin port
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(rt1, 'test.Sink', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(rt1, src, 'out', 'integer',
                                            port_properties={'routing': 'round-robin', 'nbr_peers': 2})

        request_handler.connect(rt1, snk1, 'token', rt1.id, src, 'integer')
        request_handler.connect(rt1, snk2, 'token', rt1.id, src, 'integer')

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = actual_tokens(rt1, snk1, 10)
        actual2 = actual_tokens(rt1, snk2, 10)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt1, snk1)
        request_handler.delete_actor(rt1, snk2)

#@pytest.mark.essential
class TestNullPorts(CalvinSecureTestBase):

    def testVoidActor(self):
        # Verify that the null port of a flow.Void actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src1 : std.Counter()
            src2 : flow.Void()
            join : flow.Join()
            snk  : test.Sink(store_tokens=1, quiet=1)

            src1.integer > join.token_1
            src2.void > join.token_2
            join.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testVoidActor")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testVoidActor:snk']
        actual = wait_for_tokens(rt1, snk, 10)
        expected = list(range(1, 10))
        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

    def testTerminatorActor(self):
        # Verify that the null port of a flow.Terminator actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src  : std.Counter()
            term : flow.Terminator()
            snk  : test.Sink(store_tokens=1, quiet=1)

            src.integer > term.void
            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testTerminatorActor")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testTerminatorActor:snk']
        actual = wait_for_tokens(rt1, snk)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

#@pytest.mark.essential
class TestCompare(CalvinSecureTestBase):

    def testBadOp(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5)
            pred  : std.Compare(rel="<>")
            snk   : test.Sink(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadOp")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testBadOp:snk']
        actual = wait_for_tokens(rt1, snk, 10)
        expected = [0] * 10

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5)
            pred  : std.Compare(rel="=")
            snk   : test.Sink(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testEqual")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testEqual:snk']

        expected = [x == 5 for x in range(1, 10)]
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


    def testGreaterThanOrEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5)
            pred  : std.Compare(rel=">=")
            snk   : test.Sink(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testGreaterThanOrEqual")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testGreaterThanOrEqual:snk']
        expected = [x >= 5 for x in range(1, 10)]
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

#@pytest.mark.essential
class TestSelect(CalvinSecureTestBase):

    def testTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=true)
            route : flow.Select()
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > snk.token
            route.case_false > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testTrue")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testTrue:snk']
        actual = wait_for_tokens(rt1, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=0)
            route : flow.Select()
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testFalse")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testFalse:snk']

        actual = wait_for_tokens(rt1, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


    def testBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=2)
            route : flow.Select()
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadSelect")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testBadSelect:snk']
        actual = wait_for_tokens(rt1, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

#@pytest.mark.essential
class TestDeselect(CalvinSecureTestBase):

    def testDeselectTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0)
            const_1 : std.Constant(data=1)
            comp    : std.Compare(rel="<=")
            ds      : flow.Deselect()
            snk     : test.Sink(store_tokens=1, quiet=1)

            const_0.token > ds.case_false
            const_1.token > ds.case_true
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectTrue")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testDeselectTrue:snk']

        expected = [1] * 5 + [0] * 5
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)
        helpers.destroy_app(d)

    def testDeselectFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0)
            const_1 : std.Constant(data=1)
            comp    : std.Compare(rel="<=")
            ds      : flow.Deselect()
            snk     : test.Sink(store_tokens=1, quiet=1)

            const_0.token > ds.case_true
            const_1.token > ds.case_false
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectFalse")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testDeselectFalse:snk']

        expected = [0] * 5 + [1] * 5
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


    def testDeselectBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0)
            ds      : flow.Deselect()
            snk     : test.Sink(store_tokens=1, quiet=1)

            const_0.token > ds.case_false
            src.integer > ds.case_true
            const_0.token > const_5.in
            const_5.out > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectBadSelect")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testDeselectBadSelect:snk']

        expected = [0] * 10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

#@pytest.mark.essential
class TestLineJoin(CalvinSecureTestBase):

    def testBasicJoin(self):
        _log.analyze("TESTRUN", "+", {})
        datafile = absolute_filename('data.txt')
        script = """
            fname : std.Constant(data="%s")
            src   : io.FileReader()
            join  : text.LineJoin()
            snk   : test.Sink(store_tokens=1, quiet=1)

            fname.token > src.filename
            src.out   > join.line
            join.text > snk.token
        """ % (datafile, )

        app_info, errors, warnings = self.compile_script(script, "testBasicJoin")
        print errors

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        with open(datafile, "r") as fp:
            expected = ["\n".join([l.rstrip() for l in fp.readlines()])]

        snk = d.actor_map['testBasicJoin:snk']

        actual = wait_for_tokens(rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


#@pytest.mark.essential
class TestRegex(CalvinSecureTestBase):

    def testRegexMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632")
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMatch")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testRegexMatch:snk']

        expected = ["24.1632"]
        actual = wait_for_tokens(rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)



    def testRegexNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632")
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexNoMatch")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testRegexNoMatch:snk']
        expected = ["x24.1632"]
        actual = wait_for_tokens(rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632")
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCapture")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testRegexCapture:snk']

        expected = ["24"]
        actual = wait_for_tokens(rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexMultiCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632")
            regex : text.RegexMatch(regex=!"(\d+)\.(\d+)")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMultiCapture")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testRegexMultiCapture:snk']

        expected = ["24"]
        actual = wait_for_tokens(rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexCaptureNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632")
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : test.Sink(store_tokens=1, quiet=1)
            term  : flow.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCaptureNoMatch")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testRegexCaptureNoMatch:snk']
        expected = ["x24.1632"]
        actual = wait_for_tokens(rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


#@pytest.mark.essential
class TestConstantAsArguments(CalvinSecureTestBase):

    def testConstant(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = 42
            src   : std.Constant(data=FOO)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstant")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testConstant:snk']

        expected = [42]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantRecursive(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = 42
            src   : std.Constant(data=FOO)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursive")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testConstantRecursive:snk']

        expected = [42]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


#@pytest.mark.essential
class TestConstantOnPort(CalvinSecureTestBase):

    def testLiteralOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            snk   : test.Sink(store_tokens=1, quiet=1)
            42 > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPort")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)
        time.sleep(.1)

        snk = d.actor_map['testLiteralOnPort:snk']

        expected = [42]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = "Hello"
            snk   : test.Sink(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnPort")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testConstantOnPort:snk']

        expected = ["Hello"]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantRecursiveOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = "yay"
            snk   : test.Sink(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursiveOnPort")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testConstantRecursiveOnPort:snk']

        expected = ["yay"]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


#@pytest.mark.essential
class TestConstantAndComponents(CalvinSecureTestBase):

    def testLiteralOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Foo() -> out {
                i:std.Stringify()
                42 > i.in
                i.out > .out
            }
            src   : Foo()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnCompPort")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testLiteralOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define MEANING = 42
            component Foo() -> out {
                i:std.Stringify()
                MEANING > i.in
                i.out > .out
            }
            src   : Foo()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnCompPort")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testConstantOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testStringConstantOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define MEANING = "42"
            component Foo() -> out {
                i:std.Identity()
                MEANING > i.token
                i.token > .out
            }
            src   : Foo()
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testStringConstantOnCompPort")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testStringConstantOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


#@pytest.mark.essential
class TestConstantAndComponentsArguments(CalvinSecureTestBase):

    def testComponentArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(len) -> seq {
            src : test.FiniteCounter(start=1, steps=len)
            src.integer > .seq
        }
        src : Count(len=5)
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgument")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testComponentArgument:snk']

        expected = [1,2,3,4,5]
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=5)

        helpers.destroy_app(d)

    def testComponentConstantArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 5
        component Count(len) -> seq {
            src : test.FiniteCounter(start=1, steps=len)
            src.integer > .seq
        }
        src : Count(len=FOO)
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgument")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgument:snk']

        expected = [1,2,3,4,5]
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=5)

        helpers.destroy_app(d)


    def testComponentConstantArgumentDirect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 10
        component Count() -> seq {
         src : test.FiniteCounter(start=1, steps=FOO)
         src.integer > .seq
        }
        src : Count()
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentDirect")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgumentDirect:snk']

        expected = [1,2,3,4,5,6,7,8,9,10]
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testComponentArgumentAsImplicitActor(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(data) -> seq {
            i : std.Identity()
            data > i.token
            i.token > .seq
        }
        src : Count(data="hup")
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgumentAsImplicitActor")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testComponentArgumentAsImplicitActor:snk']

        expected = ["hup"]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testComponentConstantArgumentAsImplicitActor(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = "hup"
        component Count(data) -> seq {
            i : std.Identity()
            data > i.token
            i.token > .seq
        }
        src : Count(data=FOO)
        snk : test.Sink(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentAsImplicitActor")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgumentAsImplicitActor:snk']

        expected = ["hup"]*10
        actual = wait_for_tokens(rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)
        d.destroy()

#@pytest.mark.essential
class TestConstantifyOnPort(CalvinSecureTestBase):

    def testLiteralOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk : test.Sink(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPort")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testLiteralOnPort:snk']

        actual = wait_for_tokens(rt1, snk, 10)
        expected = ['X']*len(actual)

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testLiteralOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk1.token, snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPortlist")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk1 = d.actor_map['testLiteralOnPortlist:snk1']
        snk2 = d.actor_map['testLiteralOnPortlist:snk2']

        actual1 = wait_for_tokens(rt1, snk1, 10)
        actual2 = wait_for_tokens(rt1, snk2, 10)

        expected1 = ['X']*len(actual1)
        expected2 = range(1, len(actual2))

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testLiteralsOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk1.token, /"Y"/ snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralsOnPortlist")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk1 = d.actor_map['testLiteralsOnPortlist:snk1']
        snk2 = d.actor_map['testLiteralsOnPortlist:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 10)
        actual2 = wait_for_tokens(rt1, snk2, 10)

        expected1 = ['X']*len(actual1)
        expected2 = ['Y']*len(actual2)

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testConstantsOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = "X"
            define BAR = "Y"
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1)
            snk2 : test.Sink(store_tokens=1, quiet=1)
            src.integer > /FOO/ snk1.token, /BAR/ snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantsOnPortlist")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk1 = d.actor_map['testConstantsOnPortlist:snk1']
        snk2 = d.actor_map['testConstantsOnPortlist:snk2']

        actual1 = wait_for_tokens(rt1, snk1, 10)
        actual2 = wait_for_tokens(rt1, snk2, 10)
        expected1 = ['X']*len(actual1)
        expected2 = ['Y']*len(actual2)

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testLiteralOnComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Ticker() trigger -> out {
                id : std.Identity()
                .trigger > /"X"/ id.token
                id.token > .out
            }

            tick : std.Trigger(data="tick", tick=0.1)
            ticker : Ticker()
            test : test.Sink(store_tokens=1, quiet=1)

            tick.data > ticker.trigger
            ticker.out > test.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnComponentInPort")
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        deploy_app(d)

        snk = d.actor_map['testLiteralOnComponentInPort:test']

        actual = wait_for_tokens(rt1, snk, 10)
        expected = ['X']*len(actual)

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()


#@pytest.mark.essential
class TestPortProperties(CalvinSecureTestBase):

    def testRoundRobin(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyOutsideComponentOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq(routing="round-robin")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self. get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyOutsideComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing="round-robin")
            snk1.seq(test1="dummy1")
            snk2.seq(test1="dummy2")
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk1:compsnk', 'token', 'in', 'test1') == 'dummy1')
        assert 'port' in app_info['port_properties']['testScript:snk2:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk2:compsnk', 'token', 'in', 'test1') == 'dummy2')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing="round-robin")
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
                compsnk.token(test1="dummyx")
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing="round-robin")
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk1:compsnk', 'token', 'in', 'test1') == 'dummyx')
        assert 'port' in app_info['port_properties']['testScript:snk2:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk2:compsnk', 'token', 'in', 'test1') == 'dummyx')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentInternalInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                .seq(test1="dummyx")
                compsrc.integer(routing="round-robin")
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1'][0]
        assert (app_info['port_properties']['testScript:snk1'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1') == 'dummyx')
        assert 'port' in app_info['port_properties']['testScript:snk2'][0]
        assert (app_info['port_properties']['testScript:snk2'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test1') == 'dummyx')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyInsideComponentInternalOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
                .seq(routing="round-robin")
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing') == 'round-robin')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyTupleOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')[0] == 'round-robin')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')[1] == 'random')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyConsolidateOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq(routing=["dummy", "round-robin"])
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert len(errors) == 0
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert len(self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')) == 1
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing')[0] == 'round-robin')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    @pytest.mark.xfail(reason="Line numbers are not properly propagated for error reporting")
    def testPortPropertyConsolidateRejectOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.seq(routing="fanout")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert len(errors) == 2
        assert all([e['reason'] == "Can't handle conflicting properties without common alternatives" for e in errors])
        assert all([e['line'] in [5, 11] for e in errors])

    def testPortPropertyConsolidateInsideComponentInternalOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : test.Sink(store_tokens=1, quiet=1)
                .seq > compsnk.token
                .seq(routing=["random", "round-robin", "fanout"])
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing=["round-robin", "random"])
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert len(self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing')) == 2
        assert (self.get_port_property(app_info, 'testScript:src', 'integer', 'out', 'routing')[0] == 'round-robin')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

    def testPortPropertyConsolidateInsideComponentInternalInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                .seq(test1=["dummyx", "dummyy", "dummyz"], test2="dummyi")
                compsrc.integer(routing="round-robin")
            }

            src    : CompCounter()
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            snk1.token(test1=["dummyz", "dummyy"])
            snk2.token(test1="dummyy")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (self.get_port_property(app_info, 'testScript:src:compsrc', 'integer', 'out', 'routing') == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1'][0]
        assert (app_info['port_properties']['testScript:snk1'][0]['port'] ==
                'token')
        assert len(self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1')) == 2
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1')[0] == 'dummyz')
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test1')[1] == 'dummyy')
        assert (self.get_port_property(app_info, 'testScript:snk1', 'token', 'in', 'test2') == 'dummyi')
        assert 'port' in app_info['port_properties']['testScript:snk2'][0]
        assert (app_info['port_properties']['testScript:snk2'][0]['port'] ==
                'token')
        assert len(self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test1')) == 1
        assert (self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test1')[0] == 'dummyy')
        assert (self.get_port_property(app_info, 'testScript:snk2', 'token', 'in', 'test2') == 'dummyi')

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        actual1 = wait_for_tokens(rt1, snk1, 11)
        actual2 = wait_for_tokens(rt1, snk2, 11)

        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        helpers.destroy_app(d)

#@pytest.mark.essential
class TestCollectPort(CalvinSecureTestBase):

    def testCollectPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert 'testCollectPort:snk' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testCollectPort:snk'][0]
        assert (app_info['port_properties']['testCollectPort:snk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testCollectPort:snk', 'token', 'in', 'nbr_peers') == 2)

        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk = d.actor_map['testCollectPort:snk']
        actual = wait_for_tokens(rt1, snk, 10)

        high = [x for x in actual if x > 999]
        low = [x for x in actual if x < 999]
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        helpers.destroy_app(d)

    def testCollectPortComponentIn(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Dual() seqin -> seqout1, seqout2 {
            id1    : std.Identity()
            id2    : std.Identity()
            .seqin(routing="round-robin")
            .seqin > id1.token
            .seqin > id2.token
            id1.token > .seqout1
            id2.token > .seqout2
        }
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        duo: Dual()
        duo.seqin(routing="collect-unordered")
        snk1 : test.Sink(store_tokens=1, quiet=1)
        snk2 : test.Sink(store_tokens=1, quiet=1)
        src1.integer > duo.seqin
        src2.integer > duo.seqin
        duo.seqout1 > snk1.token
        duo.seqout2 > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:duo:id1'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:duo:id2'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testCollectPort:duo:id1', 'token', 'in', 'nbr_peers') == 2)
        assert (self.get_port_property(app_info, 'testCollectPort:duo:id2', 'token', 'in', 'nbr_peers') == 2)
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testCollectPort:snk1']
        snk2 = d.actor_map['testCollectPort:snk2']
        actual1, actual2 = actual_tokens_multiple(rt1, [snk1, snk2], 10)

        high = sorted([x for x in actual1 + actual2 if x > 999])
        low = sorted([x for x in actual1 + actual2 if x < 999])
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        helpers.destroy_app(d)

    def testCollectPortComponentOut(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Dual() seqin1, seqin2 -> seqout {
            id1    : std.Identity()
            id2    : std.Identity()
            .seqout(routing="collect-unordered")
            .seqin1 > id1.token
            .seqin2 > id2.token
            id1.token > .seqout
            id2.token > .seqout
        }
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        duo: Dual()
        duo.seqout(routing="round-robin")
        snk1 : test.Sink(store_tokens=1, quiet=1)
        snk2 : test.Sink(store_tokens=1, quiet=1)
        src1.integer > duo.seqin1
        src2.integer > duo.seqin2
        duo.seqout > snk1.token
        duo.seqout > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:snk1'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:snk2'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testCollectPort:snk1', 'token', 'in', 'nbr_peers') == 2)
        assert (self.get_port_property(app_info, 'testCollectPort:snk2', 'token', 'in', 'nbr_peers') == 2)
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()

        snk1 = d.actor_map['testCollectPort:snk1']
        snk2 = d.actor_map['testCollectPort:snk2']
        actual1, actual2 = actual_tokens_multiple(rt1, [snk1, snk2], 10)

        high = sorted([x for x in actual1 + actual2 if x > 999])
        low = sorted([x for x in actual1 + actual2 if x < 999])
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        helpers.destroy_app(d)

    def testCollectPortRemote(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:snk'][0]['port'] ==
                'token')
        assert (self.get_port_property(app_info, 'testCollectPort:snk', 'token', 'in', 'nbr_peers') == 2)
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        self.migrate(rt1, rt2, snk)
        actual = wait_for_tokens(rt2, snk, 10)

        high = [x for x in actual if x > 999]
        low = [x for x in actual if x < 999]
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)
        helpers.destroy_app(d)


#@pytest.mark.essential
class TestPortRouting(CalvinSecureTestBase):
    @pytest.mark.xfail
    def testCollectPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals
        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testCollectPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src2 = d.actor_map['testCollectPort:src2']
        self.migrate(rt1, rt2, src2)
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testCollectPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src1 = d.actor_map['testCollectPort:src1']
        src2 = d.actor_map['testCollectPort:src2']
        self.migrate(rt1, rt2, src1)
        self.migrate(rt1, rt3, src2)
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testCollectTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testCollectTagPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src2 = d.actor_map['testCollectPort:src2']
        self.migrate(rt1, rt2, src2)
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            assert len(actuals[i]) < len(actuals[i+1])
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testCollectTagPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src1 = d.actor_map['testCollectPort:src1']
        src2 = d.actor_map['testCollectPort:src2']
        self.migrate(rt1, rt2, src1)
        self.migrate(rt1, rt3, src2)
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testCollectAllTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-all-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            temp = wait_for_tokens(fr, snk, len(actuals[i]))
            actuals.append(temp)
#            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==2 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([k for t in actuals[-1][len(actuals[-2])+1:] for k in t.keys()])
        # Check that src_one tag is there before migration
        assert "src_one" in set([k for t in actuals[1] for k in t.keys()])

        high = [x['src_two'] for x in actuals[-1]]
        low = [x['src_one'] for x in actuals[-1]]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testCollectAnyTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-any-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t) in [1, 2] for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([k for t in actuals[-1][len(actuals[-2])+1:] for k in t.keys()])
        # Check that src_one tag is there before migration
        assert "src_one" in set([k for t in actuals[1] for k in t.keys()])

        high = [x['src_two'] for x in actuals[-1] if 'src_two' in x]
        low = [x['src_one'] for x in actuals[-1] if 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectOneTagPortWithException(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : test.FiniteCounter(start=1, steps=3, repeat=true)
        src2 : test.FiniteCounter(start=1001, steps=100)
        expt : exception.ExceptionHandler(replace=true, replacement="exception")
        snk : test.Sink(store_tokens=1, quiet=1)
        exptsnk : test.Sink(store_tokens=1, quiet=1)
        expt.token[in](routing="collect-tagged")
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > expt.token
        src2.integer > expt.token
        expt.token > snk.token
        expt.status > exptsnk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        exptsnk = d.actor_map['testCollectPort:exptsnk']
        exceptions = wait_for_tokens(rt1, exptsnk, 10)
        actual = request_handler.report(rt1, snk)
        assert len(actual) >= 3 * 10
        print actual, exceptions

        self.assert_lists_equal(exceptions, [{u'src_one': u'End of stream'}]*10)
        high = [x['src_two'] for x in actual if isinstance(x, dict) and 'src_two' in x]
        low = [x['src_one'] for x in actual if isinstance(x, dict) and 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high, min_length=15)
        self.assert_lists_equal(range(1,4)*10, low, min_length=15)

        helpers.destroy_app(d)

    def testCollectAnyTagPortWithException(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : test.FiniteCounter(start=1, steps=3, repeat=true)
        src2 : test.FiniteCounter(start=1001, steps=100)
        expt : exception.ExceptionHandler(replace=true, replacement="exception")
        snk : test.Sink(store_tokens=1, quiet=1)
        exptsnk : test.Sink(store_tokens=1, quiet=1)
        expt.token[in](routing="collect-any-tagged")
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > expt.token
        src2.integer > expt.token
        expt.token > snk.token
        expt.status > exptsnk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        exptsnk = d.actor_map['testCollectPort:exptsnk']
        exceptions = wait_for_tokens(rt1, exptsnk, 10)
        actual = request_handler.report(rt1, snk)
        assert len(actual) >= 3 * 10
        print actual, exceptions

        self.assert_lists_equal(exceptions, [{u'src_one': u'End of stream'}]*10)
        high = [x['src_two'] for x in actual if isinstance(x, dict) and 'src_two' in x]
        low = [x['src_one'] for x in actual if isinstance(x, dict) and 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high, min_length=15)
        self.assert_lists_equal(range(1,4)*10, low, min_length=15)

        helpers.destroy_app(d)

    def testCollectAllTagPortWithException(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : test.FiniteCounter(start=1, steps=3, repeat=true)
        src2 : test.FiniteCounter(start=1001, steps=100)
        expt : exception.ExceptionHandler(replace=true, replacement="exception")
        snk : test.Sink(store_tokens=1, quiet=1)
        exptsnk : test.Sink(store_tokens=1, quiet=1)
        expt.token[in](routing="collect-all-tagged")
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > expt.token
        src2.integer > expt.token
        expt.token > snk.token
        expt.status > exptsnk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        exptsnk = d.actor_map['testCollectPort:exptsnk']
        exceptions = wait_for_tokens(rt1, exptsnk, 10)
        actual = request_handler.report(rt1, snk)
        assert len(actual) >= 3 * 10
        print actual, exceptions

        self.assert_lists_equal(exceptions, [{u'src_one': u'End of stream'}]*10)
        high = [x['src_two'] for x in actual if isinstance(x, dict) and 'src_two' in x]
        low = [x['src_one'] for x in actual if isinstance(x, dict) and 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high, min_length=15)
        self.assert_lists_equal(range(1,4)*10, low, min_length=15)

        # Test that kept in sync but skewed one token for every exception
        comp = [x['src_two'] - x['src_one'] - 1000 for x in actual if isinstance(x, dict)]
        self.assert_lists_equal(range(0,45,3), comp[0::3], min_length=5)
        self.assert_lists_equal(range(0,45,3), comp[1::3], min_length=5)
        self.assert_lists_equal(range(0,45,3), comp[2::3], min_length=5)
        helpers.destroy_app(d)

    def testRoundRobinPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple(fr, [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(fr, to, snk2)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1][:-4], min_length=20)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1][:-4], min_length=20)

        helpers.destroy_app(d)

    def testRoundRobinPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']
        self.migrate(rt1, rt2, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1][:-4], min_length=20)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1][:-4], min_length=20)

        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testRoundRobinPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        snk1_meta = request_handler.get_actor(rt1, snk1)
        snk2_meta = request_handler.get_actor(rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']
        self.migrate(rt1, rt2, snk1)
        self.migrate(rt1, rt3, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [rt2, rt3]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1][:-4], min_length=20)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1][:-4], min_length=20)

        helpers.destroy_app(d)

    @pytest.mark.xfail
    def testRandomPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple(fr, [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(fr, to, snk2)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1])[:-4], min_length=40)

        helpers.destroy_app(d)

    def testRandomPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        self.migrate(rt1, rt2, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1])[:-4], min_length=40)

        helpers.destroy_app(d)

    def testRandomPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        self.migrate(rt1, rt2, snk1)
        self.migrate(rt1, rt3, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [rt2, rt3]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1])[:-4], min_length=40)

        helpers.destroy_app(d)

    def testActorPortProperty(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Col() token -> token {
            col : flow.Collect()
            .token > col.token
            col.token > .token
        }
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        colcomp : Col()
        snk : test.Sink(store_tokens=1, quiet=1)
        src1.integer > colcomp.token
        src2.integer > colcomp.token
        colcomp.token > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testActorPortProperty")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(rt1, app_info, request_handler=request_handler)
        d.deploy()
        snk = d.actor_map['testActorPortProperty:snk']
        actuals = [[]]
        rts = [rt1, rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, i*10))
            self.migrate(fr, to, snk)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=15)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=15)
        helpers.destroy_app(d)

#@pytest.mark.essential
@pytest.mark.slow
class TestDeployScript(CalvinSecureTestBase):

    def testDeployScriptSimple(self):
        script = r"""
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token

      rule simple: node_attr_match(index=["node_name", {"organization": "com.ericsson"}])
      apply src, snk: simple
        """

        rt = rt1
        response = helpers.deploy_script(request_handler, "simple", script, rt)

        print response
        src = response['actor_map']['simple:src']
        snk = response['actor_map']['simple:snk']
        rt_src = request_handler.get_node(rt, response['placement'][src][0])["control_uris"]
        rt_snk = request_handler.get_node(rt, response['placement'][snk][0])["control_uris"]

        assert response["requirements_fulfilled"]

        wait_for_tokens(rt_src[0], snk)
        expected = expected_tokens(rt_src[0], src, 'seq')
        actual = actual_tokens(rt_snk[0], snk, len(expected))
        request_handler.disconnect(rt_src[0], src)

        self.assert_lists_equal(expected, actual)
        helpers.delete_app(request_handler, rt, response['application_id'])


@pytest.fixture(params=[("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")])
def rt_order3(request):
    return [globals()[p] for p in request.param]


@pytest.fixture(params=[1, 4])
def nbr_replicas(request):
    return request.param

import numbers
from collections import Counter


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
    request_handler.migrate(source, actor, dest.id)
    wait_for_migration(dest, [actor])

@pytest.mark.skipif(
    calvinconfig.get().get("testing","proxy_storage") != 1 and 
    calvinconfig.get().get("testing","force_replication") != 1,
    reason="Will fail on some systems with DHT")
#@pytest.mark.essential
@pytest.mark.slow
class TestReplication(object):
    def testSimpleReplication(self, rt_order3, nbr_replicas):
        _log.analyze("TESTRUN", "+", {})
        script = r"""
            src   : std.Counter()
            proc  : test.TestProcess(eval_str="data + kwargs[\"base\"]",
                        replicate_str="state.kwargs[\"base\"] = 10000 * state.replication_count",
                        kwargs={"base": 0}, dump=false)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-unordered")
            src.integer > proc.data
            proc.result > snk.token
        """
        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        response = helpers.deploy_script(request_handler, "testScript", script, rt1)

        src = response['actor_map']['testScript:src']
        proc = response['actor_map']['testScript:proc']
        snk = response['actor_map']['testScript:snk']

        migrate(rt1, rt2, proc)

        wait_until_nbr(rt1, src, 8)

        proc_rep = []
        for n in range(nbr_replicas):
            result = request_handler.replicate(rt2, proc, dst_id=rt3.id)
            print n, result
            proc_rep.append(result['actor_id'])
        actual1 = request_handler.report(rt1, snk)

        actual2 = wait_for_tokens(rt1, snk, len(actual1) + 100)
        request_handler.report(rt1, src, kwargs={'stopped': True})
        expected = expected_tokens(rt1, src, 'seq')
        actual2 = wait_for_tokens(rt1, snk, len(expected))
        # Token can take either way, but only one of each count value
        actual_mod = sorted([t % 10000 for t in actual2])
        #print expected
        #print actual_mod
        assert_lists_equal(expected, actual_mod, min_length=len(actual1)+100)
        # Check OK distribution of paths
        dist = Counter([t // 10000 for t in actual2])
        print dist
        assert all([dist.values() > 10])
        assert len(dist) == (nbr_replicas + 1)

        #print request_handler.report(rt2, proc, kwargs={'cmd_str': "self.state()"})

        # Make sure none is stalled
        request_handler.report(rt1, src, kwargs={'stopped': False})
        actual3 = wait_for_tokens(rt1, snk, len(expected) + 100)
        dist2 = Counter([t // 10000 for t in actual3])
        print dist2
        assert all([dist[k] < dist2[k] for k in dist.keys()])

        helpers.delete_app(request_handler, rt1, response['application_id'],
                           check_actor_ids=response['actor_map'].values()+ proc_rep)
        # Check all actors and replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        assert src not in actors
        assert snk not in actors
        assert proc not in actors
        for p in proc_rep:
            assert p not in actors

    def testSimpleDereplication(self, rt_order3, nbr_replicas):
        _log.analyze("TESTRUN", "+", {})
        script = r"""
            src   : std.Counter()
            proc  : test.TestProcess(eval_str="data + kwargs[\"base\"]",
                        replicate_str="state.kwargs[\"base\"] = 10000 * state.replication_count",
                        kwargs={"base": 0}, dump=false)
            snk   : test.Sink(store_tokens=1, quiet=1, active=true)
            src.integer(routing="random")
            snk.token(routing="collect-unordered")
            src.integer > proc.data
            proc.result > snk.token
        """
        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        response = helpers.deploy_script(request_handler, "testScript", script, rt1)

        src = response['actor_map']['testScript:src']
        proc = response['actor_map']['testScript:proc']
        snk = response['actor_map']['testScript:snk']

        migrate(rt1, rt2, proc)

        wait_until_nbr(rt1, src, 8)

        proc_rep = []
        for n in range(nbr_replicas):
            result = request_handler.replicate(rt2, proc, dst_id=rt3.id)
            print n, result
            proc_rep.append(result['actor_id'])
        actual1 = request_handler.report(rt1, snk)

        actual2 = wait_for_tokens(rt1, snk, len(actual1) + 100)
        # Pause sink, fill the queues a bit
        request_handler.report(rt1, snk, kwargs={'active': False})
        time.sleep(0.1)

        # Dereplicate
        async_results = []
        proc_derep = []
        for n in range(nbr_replicas):
            async_results.append(request_handler.async_replicate(rt2, proc, dereplicate=True, exhaust=True))
            if n == 0:
                # let the tokens flow again, but no new tokens
                request_handler.report(rt1, snk, kwargs={'active': True})
                request_handler.report(rt1, src, kwargs={'stopped': True})
            # Need to wait for first dereplication to finish before a second, since no simultaneous (de)replications
            proc_derep.append(request_handler.async_response(async_results[-1]))
        print proc_derep
        expected = expected_tokens(rt1, src, 'seq')
        actual2 = wait_for_tokens(rt1, snk, len(expected))

        # Check replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        for p in proc_rep:
            assert p not in actors

        # Token can take either way, but only one of each count value
        actual_mod = sorted([t % 10000 for t in actual2])
        #print expected
        #print actual_mod
        assert_lists_equal(expected, actual_mod, min_length=len(actual1)+100)
        # Check OK distribution of paths
        dist = Counter([t // 10000 for t in actual2])
        print dist
        assert all([dist.values() > 10])
        assert len(dist) == (nbr_replicas + 1)

        #print request_handler.report(rt2, proc, kwargs={'cmd_str': "self.state()"})

        helpers.delete_app(request_handler, rt1, response['application_id'],
                           check_actor_ids=response['actor_map'].values()+ proc_rep)
        # Check all actors and replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        assert src not in actors
        assert snk not in actors
        assert proc not in actors
        for p in proc_rep:
            assert p not in actors

    def testMultiDereplication(self, rt_order3, nbr_replicas):
        _log.analyze("TESTRUN", "+", {})
        script = r"""
            src   : test.FiniteCounter(start=1)
            proc  : test.TestProcess(eval_str="{data.keys()[0]: data.values()[0] + kwargs[\"base\"]}",
                        replicate_str="state.kwargs[\"base\"] = 10000 * state.replication_count",
                        kwargs={"base": 0}, dump=false)
            snk   : test.Sink(store_tokens=1, quiet=1, active=true)
            src.integer(routing="random")
            proc.data(routing="collect-tagged")
            snk.token(routing="collect-unordered")
            src.integer > proc.data
            proc.result > snk.token
        """
        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        response = helpers.deploy_script(request_handler, "testScript", script, rt1)

        src = response['actor_map']['testScript:src']
        proc = response['actor_map']['testScript:proc']
        snk = response['actor_map']['testScript:snk']
        meta = request_handler.get_actor(rt1, src)
        src_port = [meta['outports'][0]['id']]

        migrate(rt1, rt2, proc)

        wait_until_nbr(rt1, src, 8)

        # Replicate
        proc_rep = []
        src_rep = []
        for n in range(nbr_replicas):
            # Replicate connected actors simultaneously
            proc_result = request_handler.async_replicate(rt2, proc, dst_id=rt3.id)
            src_result = request_handler.async_replicate(rt1, src)

            # ... but wait for each pair, since not allowed to (de)replicate multiple at the same time
            proc_rep.append(request_handler.async_response(proc_result)['actor_id'])
            src_rep.append(request_handler.async_response(src_result)['actor_id'])
            meta = request_handler.get_actor(rt1, src_rep[-1])
            src_port.append(meta['outports'][0]['id'])
        actual1 = request_handler.report(rt1, snk)

        actual2 = wait_for_tokens(rt1, snk, (nbr_replicas + 1) * len(actual1) + 100)
        # Pause sink, fill the queues a bit
        request_handler.report(rt1, snk, kwargs={'active': False})
        time.sleep(0.1)

        # No new tokens
        request_handler.report(rt1, src, kwargs={'stopped': True})
        for r in src_rep:
            request_handler.report(rt1, r, kwargs={'stopped': True})
        expected = [expected_tokens(rt1, src, 'seq')]
        for r in src_rep:
            expected.append(expected_tokens(rt1, r, 'seq'))

        # Dereplicate
        proc_derep = []
        src_derep = []
        for n in range(nbr_replicas):
            # Dereplicate connected actors simultaneously
            proc_result = request_handler.async_replicate(rt2, proc, dereplicate=True, exhaust=True)
            src_result = request_handler.async_replicate(rt1, src, dereplicate=True, exhaust=True)
            if n == 0:
                # let the tokens flow again in the sink
                request_handler.report(rt1, snk, kwargs={'active': True})
            # ... but wait for each pair, since not allowed to (de)replicate multiple at the same time
            proc_derep.append(request_handler.async_response(proc_result))
            src_derep.append(request_handler.async_response(src_result))
        print proc_derep
        print src_derep

        total_len = sum([len(e) - 1 for e in expected])
        actual2 = wait_for_tokens(rt1, snk, total_len)

        # Check replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        for a in proc_rep:
            assert a not in actors
        for a in src_rep:
            assert a not in actors

        # Token can take either way, but only up to nbr_replicas of each count value
        actuals = []
        actuals_rem = []
        actuals_mod = []
        for p in src_port:
            actuals.append([t[p] for t in actual2 if p in t])
            actuals_rem.append(sorted([t % 10000 for t in actuals[-1]]))
            actuals_mod.extend([t // 10000 for t in actuals[-1]])
        for i in range(nbr_replicas + 1):
            #print expected[i]
            #print actuals_rem[i]
            assert_lists_equal(expected[i], actuals_rem[i], min_length=len(expected[i])-1)
        # Check OK distribution of paths
        dist = Counter(actuals_mod)
        print dist
        assert all([dist.values() > 10])
        assert len(dist) == (nbr_replicas + 1)

        helpers.delete_app(request_handler, rt1, response['application_id'],
                           check_actor_ids=response['actor_map'].values()+ proc_rep + src_rep)
        # Check all actors and replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        assert src not in actors
        assert snk not in actors
        assert proc not in actors
        for a in proc_rep:
            assert a not in actors
        for a in src_rep:
            assert a not in actors

class TestPortmappingScript(CalvinSecureTestBase):

    def _run_test(self, script, minlen):
        rt = rt1
        response = helpers.deploy_script(request_handler, "simple", script, rt)
        snk = response['actor_map']['simple:snk']
        wait_for_tokens(rt, snk, minlen)
        actual = actual_tokens(rt, snk)
        helpers.delete_app(request_handler, rt, response['application_id'])
        return actual

    def testSimple(self):
        script = r"""
        dummy : std.Constantify(constant=42)
        cdict : flow.CollectCompleteDict(mapping={"dummy":&dummy.out})
        snk : test.Sink(store_tokens=1, quiet=1)

        1 > dummy.in
        dummy.out > cdict.token
        cdict.dict > snk.token
        """

        expected = [{u'dummy': 42}]*5
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)

    def testMapAlternate(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        input: std.Counter()
        alt: flow.Alternate(order=[&out1.out, &out2.out, &out3.out])
        out1 : text.PrefixString(prefix="tag-1:")
        out2 : text.PrefixString(prefix="tag-2:")
        out3 : text.PrefixString(prefix="tag-3:")
        input.integer > out1.in
        input.integer > out2.in
        input.integer > out3.in
        out1.out > alt.token
        out2.out > alt.token
        out3.out > alt.token
        alt.token > snk.token
        """
        expected = [
            "tag-1:1",
            "tag-2:1",
            "tag-3:1",
            "tag-1:2",
            "tag-2:2",
            "tag-3:2",
            "tag-1:3",
            "tag-2:3",
            "tag-3:3",
            "tag-1:4",
            "tag-2:4",
            "tag-3:4"
        ]
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)

    def testMapDealternate(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        input: std.Counter()
        switch: flow.Dealternate(order=[&out3.in, &out1.in, &out2.in])
        out1 : text.PrefixString(prefix="tag-1:")
        out2 : text.PrefixString(prefix="tag-2:")
        out3 : text.PrefixString(prefix="tag-3:")
        collect : flow.Alternate(order=[&out1.out, &out2.out, &out3.out])
        input.integer > switch.token
        switch.token > out1.in
        switch.token > out2.in
        switch.token > out3.in
        out1.out > collect.token
        out2.out > collect.token
        out3.out > collect.token
        collect.token > snk.token
        """
        expected = [
            "tag-1:2",
            "tag-2:3",
            "tag-3:1",
            "tag-1:5",
            "tag-2:6",
            "tag-3:4",
            "tag-1:8",
            "tag-2:9",
            "tag-3:7"
        ]
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)


    def testMapDispatchCollect(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        input: std.Counter()
        disp : flow.Dispatch()
        coll : flow.Collect()
        tag1: text.PrefixString(prefix="tag1-")
        tag2: text.PrefixString(prefix="tag2-")
        tag3: text.PrefixString(prefix="tag3-")

        input.integer > disp.token
        disp.token > tag1.in
        disp.token > tag2.in
        disp.token > tag3.in
        tag1.out > coll.token
        tag2.out > coll.token
        tag3.out > coll.token
        coll.token > snk.token
        """
        actual = self._run_test(script, 50)
        pairs = [x.split('-') for x in actual]
        tags = [p[0] for p in pairs]
        values = [int(p[1]) for p in pairs]
        assert (set(values) == set(range(1, len(actual)+1)))
        print tags
        assert set(tags) == set(["tag1", "tag2", "tag3"])

    def testMapDispatchDict(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        dd : flow.DispatchDict(mapping={"t1": &tag1.in, "t2": &tag2.in, "t3": &tag3.in})
        tag1: text.PrefixString(prefix="tag-1:")
        tag2: text.PrefixString(prefix="tag-2:")
        tag3: text.PrefixString(prefix="tag-3:")
        coll : flow.Alternate(order=[&tag1.out, &tag2.out, &tag3.out])
        {"t1": 1, "t2": 2, "t3": 3} > dd.dict
        dd.token > tag1.in
        dd.token > tag2.in
        dd.token > tag3.in
        dd.default > voidport
        tag1.out > coll.token
        tag2.out > coll.token
        tag3.out > coll.token
        coll.token > snk.token
        """

        expected = [
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
        ]
        actual = self._run_test(script, len(expected))
        self.assert_lists_equal(expected, actual)

    def testMapCollectCompleteDict(self):
        script = r"""
        snk : test.Sink(store_tokens=1, quiet=1)
        dd : flow.DispatchDict(mapping={"t1": &tag1.in, "t2": &tag2.in, "t3": &tag3.in})
        tag1: text.PrefixString(prefix="tag-1:")
        tag2: text.PrefixString(prefix="tag-2:")
        tag3: text.PrefixString(prefix="tag-3:")
        cd : flow.CollectCompleteDict(mapping={"t1": &tag2.out, "t2": &tag3.out, "t3": &tag1.out})
        {"t1": 1, "t2": 2, "t3": 3} > dd.dict
        dd.token > tag1.in
        dd.token > tag2.in
        dd.token > tag3.in
        dd.default > voidport
        tag1.out > cd.token
        tag2.out > cd.token
        tag3.out > cd.token
        cd.dict > snk.token
        """
        actual = self._run_test(script, 50)
        expected = [{u't2': 'tag-3:3', u't3': 'tag-1:1', u't1': 'tag-2:2'}]*len(actual)
        self.assert_lists_equal(expected, actual)

    @pytest.mark.xfail
    def testMapComponentPort(self):
        script = r"""
        component Dummy() in -> out {
            identity : std.Identity()
            .in > identity.token
            identity.token > .out
        }
        snk : test.Sink(store_tokens=1, quiet=1)
        dummy : Dummy()
        cdict : flow.CollectCompleteDict(mapping={"dummy":&dummy.out})
        1 > dummy.in
        dummy.out > cdict.token
        cdict.dict > snk.token
        """
        actual = self._run_test(script, 10)
        expected = [{u'dummy': 1}]*len(actual)
        self.assert_lists_equal(expected, actual)


    @pytest.mark.xfail
    def testMapComponentInternalPort(self):
        script = r"""
        component Dummy() in -> out {
            # Works with &foo.token or "foo.token" if constant has label :foo
            cdict : flow.CollectCompleteDict(mapping={"dummy":&.in})

            .in > cdict.token
            cdict.dict > .out
        }
        snk : test.Sink(store_tokens=1, quiet=1)
        dummy : Dummy()
        1 > dummy.in
        dummy.out > snk.token
        """
        actual = self._run_test(script, 10)
        expected = [{u'dummy': 1}]*len(actual)
        s
