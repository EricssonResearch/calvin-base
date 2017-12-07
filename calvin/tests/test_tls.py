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
import socket
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

homefolder = get_home()
credentials_testdir = os.path.join(homefolder, ".calvin","test_tls")
runtimesdir = os.path.join(credentials_testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="test_security_domain"
orig_application_store_path = os.path.join(security_testdir, "scripts")

hostname=None
NBR_OF_RUNTIMES=4
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
        global hostname
        global runtimes
        global rt_attributes
        global request_handler
        try:
            ipv6_hostname = socket.gethostbyaddr('::1')
        except Exception as err:
            print("Failed to resolve the IPv6 localhost hostname, please update the corresponding entry in the /etc/hosts file, e.g.,:\n"
                        "\t::1              <hostname>.localdomain <hostname>.local <hostname> localhost")
            raise
        try:
            ipv6_hostname = socket.gethostbyaddr('::ffff:127.0.0.1')
        except Exception as err:
            print("Failed to resolve ::ffff:127.0.0.1, please add the following line (with your hostname) to  /etc/hosts :\n"
                  "::ffff:127.0.0.1:           <hostname>.localdomain <hostname>.local <hostname>")
            raise
        try:
            hostname = socket.gethostname()
            ip_addr = socket.gethostbyname(hostname)
            fqdn = socket.getfqdn(hostname)
            print("\n\tip_addr={}"
                      "\n\thostname={}"
                      "\n\tfqdn={}".format(ip_addr, hostname, fqdn))
        except Exception as err:
            print("Failed to resolve the hostname, ip_addr or the FQDN of the runtime, err={}".format(err))
            raise

        try:
            shutil.rmtree(credentials_testdir)
        except Exception as err:
            print "Failed to remove old tesdir, err={}".format(err)
            pass
        try:
            os.makedirs(credentials_testdir)
            os.makedirs(runtimesdir)
            os.makedirs(runtimes_truststore)
        except Exception as err:
            _log.error("Failed to create test folder structure, err={}".format(err))
            print "Failed to create test folder structure, err={}".format(err)
            raise

        _log.info("Trying to create a new test domain configuration. Create many CAs to ensure runtime can handle several CA certificates")
        try:
            ca1 = certificate_authority.CA(domain=domain_name+" 1", commonName="testdomainCA1", security_dir=credentials_testdir)
            ca2 = certificate_authority.CA(domain=domain_name+" 2", commonName="testdomainCA2", security_dir=credentials_testdir)
            ca3 = certificate_authority.CA(domain=domain_name+" 3", commonName="testdomainCA3", security_dir=credentials_testdir)
        except Exception as err:
            _log.error("Failed to create CA, err={}".format(err))

        _log.info("Copy CA cert into truststore of runtimes folder")
        ca1.export_ca_cert(runtimes_truststore)
        ca2.export_ca_cert(runtimes_truststore)
        ca3.export_ca_cert(runtimes_truststore)

        actor_store_path, application_store_path = helpers.sign_files_for_security_tests(credentials_testdir)
        runtimes = helpers.create_CA_and_generate_runtime_certs(domain_name, credentials_testdir, NBR_OF_RUNTIMES)
        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt0_conf = copy.deepcopy(rt_conf)

        # Runtime 0: local authentication, signature verification, local authorization.
        # Primarily acts as Certificate Authority for the domain
        rt0_conf.set('global','storage_type','local')
        rt0_conf.set('security','certificate_authority',{
            'domain_name':domain_name,
            'is_ca':True
            })
        rt0_conf.save("/tmp/calvin5000.conf")

        # Runtime 1: local authentication, signature verification, local authorization.
        rt_conf.set('global','storage_type','proxy')
        rt_conf.set('global','storage_proxy',"calvinip://%s:5000" % hostname )
        rt_conf.set('security','certificate_authority',{
            'domain_name':domain_name,
            'is_ca':False
            })

        for i in range(1, NBR_OF_RUNTIMES):
            rt_conf.save("/tmp/calvin500{}.conf".format(i))

        helpers.start_all_runtimes(runtimes, hostname, request_handler, tls=True)
        request.addfinalizer(self.teardown)


    def teardown(self):
        helpers.teardown(runtimes, request_handler, hostname)


###################################
#   Signature related tests
###################################

    def test_deploy_and_migrate_with_tls(self):
        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
      src.integer > snk.token
    """
        _log.analyze("TESTRUN", "+", {})
        rt = runtimes[2]['RT']
        result = {}
        try:
            result = request_handler.deploy_application(rt, "test_script", script)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed to deploy script")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of script, no use to verify if requirements fulfilled")

        #Log actor ids:
        _log.info("Actors id:s:\n\tsrc id={}\n\tsnk={}".format(result['actor_map']['test_script:src'],
                                                                        result['actor_map']['test_script:snk']))


        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(runtimes, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_script:src'] in actors[2]
        assert result['actor_map']['test_script:snk'] in actors[2]
        time.sleep(1)
        try:
            actual = request_handler.report(rt, result['actor_map']['test_script:snk'])
        except Exception as err:
            _log.error("Failed to report from runtime 2, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 5

        time.sleep(1)
        request_handler.delete_application(rt, result['application_id'])


