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
test_name="test_automatic_ca_discovery"
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
        #This test does not really need signed actors/applications, but do it anyway to be 
        #be able to deploy application similarly as the other security tests
        helpers.sign_files_for_security_tests(credentials_testdir)

        print "Trying to create a new test domain configuration."
        ca = certificate_authority.CA(domain=domain_name, commonName="testdomain CA", security_dir=credentials_testdir)
#
        print "Copy CA cert into truststore of runtimes folder"
        ca.export_ca_cert(runtimes_truststore)
        certificate.c_rehash(type=certificate.TRUSTSTORE_TRANSPORT, security_dir=credentials_testdir)
        #Define the runtime attributes
        for i in range(NBR_OF_RUNTIMES):
             node_name ={'organization': 'org.testexample', 'name': 'testNode{}'.format(i)}
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
        runtimes=[]
        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)
        #Generate credentials, create CSR, sign with CA and import cert for all runtimes
        enrollment_passwords=[]
        for rt_attribute in rt_attributes_cpy:
            attributes=AttributeResolver(rt_attribute)
            node_name = attributes.get_node_name_as_str()
            nodeid = calvinuuid.uuid("")
            enrollment_password = ca.cert_enrollment_add_new_runtime(node_name)
            enrollment_passwords.append(enrollment_password)

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])
        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('global', 'storage_type', "securedht")

        # Runtime 0: Certificate authority.
        rt0_conf = copy.deepcopy(rt_conf)
        rt0_conf.set('security','certificate_authority',{
                    'domain_name':domain_name,
                    'is_ca':'True'
                    })
        rt0_conf.save("/tmp/calvin5000.conf")

        for i in range(1, NBR_OF_RUNTIMES):
            rt_conf.set('security','certificate_authority',
                        {
                            'domain_name':domain_name,
                            'is_ca':'False',
                            'enrollment_password': enrollment_passwords[i]
                        })
            rt_conf.save("/tmp/calvin{}.conf".format(5000+i))

        #Start all runtimes
        for i in range(NBR_OF_RUNTIMES):
            _log.info("Starting runtime {}".format(i))
            try:
                logfile = _config_pytest.getoption("logfile")+"{}".format(5000+i)
                outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
                if outfile == logfile:
                    outfile = None
            except:
                logfile = None
                outfile = None
            csruntime(hostname,
                        port=5000+i,
                        controlport=5020+i,
                        attr=rt_attributes[i],
                        loglevel=_config_pytest.getoption("loglevel"),
                        logfile=logfile,
                        outfile=outfile,
                        configfile="/tmp/calvin{}.conf".format(5000+i),
                        dht_network_filter=test_name
                     )
            rt.append(RT("https://{}:{}".format(hostname,5020+i)))
            rt[i].attributes=rt_attributes[i]
            time.sleep(0.3)
        time.sleep(10)

        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt
        global request_handler
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        for i in range(1, NBR_OF_RUNTIMES):
            _log.info("kill runtime {}".format(i))
            request_handler.quit(rt[i])
        # Kill Auth/Authz node last since the other nodes need it for authorization
        # of the kull requests
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
#   Policy related tests
###################################

    @pytest.mark.slow
    def testSecurity_deploy_and_migrate(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        start = time.time()
        try:
            helpers.security_verify_storage(rt, request_handler)
        except Exception as err:
            _log.error("Failed storage verification, err={}".format(err))
            raise
        time_to_verify_storaget = time.time()-start
        time.sleep(1)
        try:
            rt0_id = request_handler.get_node_id(rt[0])
            rt1_id = request_handler.get_node_id(rt[1])
        except Exception as err:
            _log.error("Failed to fetch runtime ids, err={}".format(err))
            raise
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_unsignedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user3", "password": "pass3"})
            result = request_handler.deploy_application(rt[0], "test_security1_unsignedApp_unsignedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed to deploy test_security1_unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_unsignedActors, no use to verify if requirements fulfilled")
        #Log actor ids:
        _log.info("Actors id:s:\n\tsrc id={}\n\tsum={}\n\tsnk={}".format(result['actor_map']['test_security1_unsignedApp_unsignedActors:src'],
                                                                        result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'],
                                                                        result['actor_map']['test_security1_unsignedApp_unsignedActors:snk']))


        # Verify that actors exist like this
        try:
            actors = helpers.fetch_and_log_runtime_actors(rt, request_handler)
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[0]
        time.sleep(1)
        try:
            actual = request_handler.report(rt[0], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        except Exception as err:
            _log.error("Failed to report from runtime 0, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 5

        time.sleep(1)
        request_handler.delete_application(rt[0], result['application_id'])


