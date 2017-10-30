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
test_name="test_securedht"
credentials_testdir = os.path.join(homefolder, ".calvin", test_name)
runtimesdir = os.path.join(credentials_testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")
runtimes_truststore_signing_path = os.path.join(runtimesdir,"truststore_for_signing")
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="test_security_domain"
code_signer_name="test_signer"
identity_provider_path = os.path.join(credentials_testdir, "identity_provider")
policy_storage_path = os.path.join(security_testdir, "policies")
orig_actor_store_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'actorstore','systemactors'))
actor_store_path = os.path.join(credentials_testdir, "store")
orig_application_store_path = os.path.join(security_testdir, "scripts")
application_store_path = os.path.join(credentials_testdir, "scripts")

NBR_OF_RUNTIMES=6

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
        import fileinput
        global runtimes
        global rt_attributes
        global request_handler
        try:
            shutil.rmtree(credentials_testdir)
        except Exception as err:
            print "Failed to remove old tesdir, err={}".format(err)
            pass
        helpers.sign_files_for_security_tests(credentials_testdir)
        runtimes = helpers.create_CA_and_generate_runtime_certs(domain_name, credentials_testdir, NBR_OF_RUNTIMES)

        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'domain_name', domain_name)
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])
        rt_conf.set('global', 'storage_type', "securedht")

        for i in range(NBR_OF_RUNTIMES):
            rt_conf.set('security','certificate_authority',{
                'domain_name':domain_name
            })
            rt_conf.save("/tmp/calvin{}.conf".format(5000+i))

        helpers.start_all_runtimes(runtimes, hostname, request_handler)
        request.addfinalizer(self.teardown)

    def teardown(self):
        helpers.teardown(runtimes, request_handler, hostname)

###################################
#   Policy related tests
###################################

    @pytest.mark.slow
    def test_deploy_and_migrate_with_securedht(self):
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token
    """
        _log.analyze("TESTRUN", "+", {})
        result = {}
        try:
            result = request_handler.deploy_application(runtimes[0]["RT"], "unsignedApp_unsignedActors", script)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed to deploy unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app unsignedApp_unsignedActors, no use to verify if requirements fulfilled")
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise

 #Log actor ids:
        _log.info("Actors id:s:\n\tsrc id={}\n\tsnk={}".format(result['actor_map']['unsignedApp_unsignedActors:src'],
                                                               result['actor_map']['unsignedApp_unsignedActors:snk']))


        # Verify that actors both src and snk are running at rt0
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['unsignedApp_unsignedActors:src'] in actors[0]
        assert result['actor_map']['unsignedApp_unsignedActors:snk'] in actors[0]
        time.sleep(1)
        try:
            actual = request_handler.report(runtimes[0]["RT"], result['actor_map']['unsignedApp_unsignedActors:snk'])
        except Exception as err:
            _log.error("Failed to report from runtime 0, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 5

        #Migrate snk actor to rt1
        time.sleep(2)
        _log.info("Let's migrate actor {} from runtime {}(rt0) to runtime {}(rt1)".format(result['actor_map']['unsignedApp_unsignedActors:snk'], runtimes[0]["id"],  runtimes[1]["id"]))
        try:
            request_handler.migrate(runtimes[0]["RT"], result['actor_map']['unsignedApp_unsignedActors:snk'], runtimes[1]["id"])
        except Exception as err:
            _log.error("Failed to send first migration request to runtime 0, err={}".format(err))
            raise
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['unsignedApp_unsignedActors:src'] in actors[0]
        assert result['actor_map']['unsignedApp_unsignedActors:snk'] in actors[1]
        time.sleep(1)
        try:
            actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['unsignedApp_unsignedActors:snk'])
        except Exception as err:
            _log.error("Failed to report snk values from runtime 1, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 3

        #Migrate src actor to rt1
        time.sleep(1)
        try:
            request_handler.migrate(runtimes[0]["RT"], result['actor_map']['unsignedApp_unsignedActors:src'], runtimes[1]["id"])
        except Exception as err:
            _log.error("Failed to send second migration requestfrom runtime 0, err={}".format(err))
            raise
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['unsignedApp_unsignedActors:src'] in actors[1]
        assert result['actor_map']['unsignedApp_unsignedActors:snk'] in actors[1]
        time.sleep(1)
        try:
            actual = request_handler.report(runtimes[1]["RT"], result['actor_map']['unsignedApp_unsignedActors:snk'])
        except Exception as err:
            _log.error("Failed to report snk values from runtime 1, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 3
        request_handler.delete_application(runtimes[0]["RT"], result['application_id'])


