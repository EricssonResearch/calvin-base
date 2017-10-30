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
credentials_testdir = os.path.join(homefolder, ".calvin","test_automatic_authenticatio_registration_dir")
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

import socket
from calvin.tests.helpers import get_ip_addr
ip_addr = get_ip_addr()
hostname = socket.gethostname()

runtimes=[]
rt_attributes=[]
request_handler=None
storage_verified=False

@pytest.mark.slow
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        global runtimes
        global rt_attributes
        global request_handler
        try:
            shutil.rmtree(credentials_testdir)
        except Exception as err:
            print "Failed to remove old testdir, err={}".format(err)
            pass
        try:
            shutil.copytree(orig_identity_provider_path, identity_provider_path)
        except Exception as err:
            _log.error("Failed to create test folder structure, err={}".format(err))
            print "Failed to create test folder structure, err={}".format(err)
            raise
        helpers.sign_files_for_security_tests(credentials_testdir)
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

        # Runtime 0: Certificate authority, authentication server, authorization server, proxy storage server.
        rt0_conf = copy.deepcopy(rt_conf)
        rt0_conf.set('global','storage_type','local')
        rt0_conf.set("security", "security_conf", {
                        "comment": "Authentication server accepting external requests",
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": identity_provider_path,
                            "accept_external_requests": True
                        }
                    })
        rt0_conf.save("/tmp/calvin5000.conf")

        # Other runtimes 
        rt_conf.set('global','storage_type','proxy')
        rt_conf.set('global','storage_proxy',"calvinip://%s:5000" % ip_addr )
        rt_conf.set("security", "security_conf", {
                        "comment": "External authentication",
                        "authentication": {
                            "procedure": "external"
                        }
                    })

        for i in range(1, NBR_OF_RUNTIMES):
            rt_conf.save("/tmp/calvin500{}.conf".format(i))

        helpers.start_all_runtimes(runtimes, hostname, request_handler)
        request.addfinalizer(self.teardown)


    def teardown(self):
        helpers.teardown_slow(runtimes, request_handler, hostname)


###################################
#   Signature related tests
###################################

    @pytest.mark.slow
    def testPositive_CorrectlySignedApp_CorrectlySignedActors(self):
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token
    """
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(runtimes[1]["RT"], "test_script", script)
        except Exception as e:
#            if e.message.startswith("401"):
#                raise Exception("Failed security verification of app test_script")
            _log.error("Test deploy failed, err={}".format(e))
            raise Exception("Failed deployment of app test_script, no use to verify if requirements fulfilled")

        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_script:src'] in actors[1]
        assert result['actor_map']['test_script:snk'] in actors[1]
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['test_script:snk'])
        print "actual=", actual
        assert len(actual) > 2

        request_handler.delete_application(runtimes[1]["RT"], result['application_id'])



