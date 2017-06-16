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
credentials_testdir = os.path.join(homefolder, ".calvin","test_automatic_authorization_registration")
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

        runtimes=[]
        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        request_handler = RequestHandler(verify=truststore_dir)
        #Let's use the admin user0 for request_handler 
        request_handler.set_credentials({"user": "user0", "password": "pass0"})

        #Generate credentials, create CSR, sign with CA and import cert for all runtimes
        enrollment_passwords=[]
        for rt_attribute in rt_attributes_cpy:
            attributes=AttributeResolver(rt_attribute)
            node_name = attributes.get_node_name_as_str()
            nodeid = calvinuuid.uuid("")
            #rt0 need authzserver extension to it's node name, which needs to be certified by the CA
            if "testNode0" in node_name:
                ca.add_new_authentication_server(node_name)
                ca.add_new_authorization_server(node_name)
            enrollment_password = ca.cert_enrollment_add_new_runtime(node_name)
            enrollment_passwords.append(enrollment_password)
            runtime=runtime_credentials.RuntimeCredentials(node_name,
                                                           domain=domain_name,
                                                           security_dir=credentials_testdir,
                                                           nodeid=nodeid,
                                                           enrollment_password=enrollment_password)
            runtimes.append(runtime)
            ca_cert = runtime.get_truststore(type=certificate.TRUSTSTORE_TRANSPORT)[0][0]
            csr_path = os.path.join(runtime.runtime_dir, node_name + ".csr")
            #Decrypt encrypted CSR with CAs private key
            rsa_encrypted_csr = runtime.get_encrypted_csr()
            csr = ca.decrypt_encrypted_csr(encrypted_enrollment_request=rsa_encrypted_csr)
            csr_path = ca.store_csr_with_enrollment_password(csr)
            cert_path = ca.sign_csr(csr_path)
            runtime.store_own_cert(certpath=cert_path, security_dir=credentials_testdir)

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])

        # Runtime 0: Certificate authority, authentication server, authorization server, proxy storage server.
        rt0_conf = copy.deepcopy(rt_conf)
        rt0_conf.set('global','storage_type','local')
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

        # Other runtimes 
        rt_conf.set('global','storage_type','proxy')
        rt_conf.set('global','storage_proxy',"calvinip://%s:5000" % ip_addr )
        rt_conf.set("security", "security_conf", {
                        "comment": "External authentication, external authorization",
                        "authentication": {
                            "procedure": "external",
                            "server_uuid": runtimes[0].node_id
                        },
                        "authorization": {
                            "procedure": "external"
#                            "procedure": "external",
#                            "server_uuid": runtimes[0].node_id
                        }
                    })

        for i in range(1, NBR_OF_RUNTIMES):
            rt_conf.save("/tmp/calvin500{}.conf".format(i))

        #Start runtime 0 as it takes alot of time to start, and needs to be up before the others start
        for i in range(0, 1):
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
            rt.append(RT("http://{}:502{}".format(hostname,i)))
            rt[0].attributes=rt_attributes[0]
        #It takes 4,5 seconds for rt0 to hash the passwords in the users_db file, so wait for that to be done
        time.sleep(5)
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
#            rt.append(RT("https://{}:502{}".format(hostname, i)))
            rt.append(RT("http://{}:502{}".format(hostname,i)))
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

        try:
            helpers.security_verify_storage(rt, request_handler)
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



