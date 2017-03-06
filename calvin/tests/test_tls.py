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

import os
import json
import copy
import socket
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

homefolder = get_home()
credentials_testdir = os.path.join(homefolder, ".calvin","test_tls_dir")
runtimesdir = os.path.join(credentials_testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")
#runtimes_truststore_signing_path = os.path.join(runtimesdir,"truststore_for_signing")
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="test_security_domain"
#code_signer_name="test_signer"
#identity_provider_path = os.path.join(credentials_testdir, "identity_provider")
#policy_storage_path = os.path.join(security_testdir, "policies")
#orig_actor_store_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'actorstore','systemactors'))
#actor_store_path = os.path.join(credentials_testdir, "store")
orig_application_store_path = os.path.join(security_testdir, "scripts")
#application_store_path = os.path.join(credentials_testdir, "scripts")

hostname=None
rt=[]
rt_attributes=[]
request_handler=None
storage_verified=False

def replace_text_in_file(file_path, text_to_be_replaced, text_to_insert):
    # Read in the file
    filedata = None
    with open(file_path, 'r') as file :
          filedata = file.read()

    # Replace the target string
    filedata = filedata.replace(text_to_be_replaced, text_to_insert)

    # Write the file out again
    with open(file_path, 'w') as file:
        file.write(filedata)

def fetch_and_log_runtime_actors():
    global rt
    # Verify that actors exist like this
    actors=[]
    for runtime in rt:
        actors.append(request_handler.get_actors(runtime))
    _log.info("\n\trt0 actors={}\n\trt1 actors={}\n\trt2 actors={}\n\trt3 actors={}\n\trt4 actors={}\n\trt5 actors={}".format(actors[0], actors[1], actors[2], actors[3], actors[4], actors[5]))
    return actors

@pytest.mark.slow
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        import fileinput
        global hostname
        global rt
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
            os.mkdir(credentials_testdir)
            os.mkdir(runtimesdir)
            os.mkdir(runtimes_truststore)
        except Exception as err:
            _log.error("Failed to create test folder structure, err={}".format(err))
            print "Failed to create test folder structure, err={}".format(err)
            raise

        _log.info("Trying to create a new test domain configuration.")
        try:
            ca = certificate_authority.CA(domain=domain_name, commonName="testdomain CA", security_dir=credentials_testdir)
        except Exception as err:
            _log.error("Failed to create CA, err={}".format(err))

        _log.info("Copy CA cert into truststore of runtimes folder")
        ca.export_ca_cert(runtimes_truststore)
        node_names = []
        rt_attributes=[]
        for i in range(6):
            node_name ={'organization': 'org.testexample', 'name': 'testNode{}'.format(i)}
            owner = {'organization': domain_name, 'personOrGroup': 'testOwner'}
            address = {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}
            rt_attribute={'indexed_public':
                            {'owner':owner,
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
        #   The following is less than optimal if multiple CA certs exist
        ca_cert_path = os.path.join(truststore_dir, os.listdir(truststore_dir)[0])
        request_handler = RequestHandler(verify=ca_cert_path)

        #Generate credentials, create CSR, sign with CA and import cert for all runtimes
        enrollment_passwords=[]
        for rt_attribute in rt_attributes_cpy:
            _log.info("rt_attribute={}".format(rt_attribute))
            attributes=AttributeResolver(rt_attribute)
            node_name = attributes.get_node_name_as_str()
            nodeid = calvinuuid.uuid("")
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
            #Encrypt CSR with CAs public key (to protect enrollment password)
            rsa_encrypted_csr = runtime.cert_enrollment_encrypt_csr(csr_path, ca_cert)
            #Decrypt encrypted CSR with CAs private key
            csr = ca.decrypt_encrypted_csr(encrypted_enrollment_request=rsa_encrypted_csr)
            csr_path = ca.store_csr_with_enrollment_password(csr)
            cert_path = ca.sign_csr(csr_path)
            runtime.store_own_cert(certpath=cert_path, security_dir=credentials_testdir)

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('security', 'domain_name', domain_name)
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt0_conf = copy.deepcopy(rt_conf)
        rt_conf.set('global','storage_type','proxy')
        rt_conf.set('global','storage_proxy',"calvinip://%s:5000" % hostname )

        # Runtime 0: local authentication, signature verification, local authorization.
        # Primarily acts as Certificate Authority for the domain
        rt0_conf.set('global','storage_type','local')
        rt0_conf.save("/tmp/calvin5000.conf")

        # Runtime 1: local authentication, signature verification, local authorization.
        rt1_conf = copy.deepcopy(rt_conf)
        rt1_conf.save("/tmp/calvin5001.conf")

        # Runtime 2: local authentication, signature verification, local authorization.
        # Can also act as authorization server for other runtimes.
        # Other street compared to the other runtimes
        rt2_conf = copy.deepcopy(rt_conf)
        rt2_conf.save("/tmp/calvin5002.conf")

        # Runtime 3: external authentication (RADIUS), signature verification, local authorization.
        rt3_conf = copy.deepcopy(rt_conf)
        rt3_conf.save("/tmp/calvin5003.conf")

        # Runtime 4: local authentication, signature verification, external authorization (runtime 2).
        rt4_conf = copy.deepcopy(rt_conf)
        rt4_conf.save("/tmp/calvin5004.conf")

        # Runtime 5: external authentication (runtime 1), signature verification, local authorization.
        rt5_conf = copy.deepcopy(rt_conf)
        rt5_conf.save("/tmp/calvin5005.conf")

        #Start all runtimes
        for i in range(len(rt_attributes)):
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
            rt.append(RT("https://{}:502{}".format(hostname, i)))
            # Wait to be sure that all runtimes has started
            time.sleep(1)
        time.sleep(2)

        request.addfinalizer(self.teardown)


    def teardown(self):
        global hostname
        global rt
        global request_handler
        for runtime in rt:
            request_handler.quit(runtime)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        for i in range(len(rt_attributes)):
            os.system("pkill -9 -f 'csruntime -n {} -p 500{}'" .format(hostname,i))
        time.sleep(0.2)

    def verify_storage(self):
        global rt
        global request_handler
        global storage_verified
        _log.info("storage_verified={}".format(storage_verified))
        if not storage_verified:
            _log.info("Let's verify storage, rt={}".format(rt))
            rt_id=[None]*len(rt)
            failed = True
            # Try 30 times waiting for control API to be up and running
            for i in range(30):
                try:
                    for j in range(len(rt)):
                        rt_id[j] = rt_id[j] or request_handler.get_node_id(rt[j])
                    failed = False
                    break
                except Exception as err:
                    _log.error("request handler failed getting node_id from runtime, attempt={}, err={}".format(j, err))
                    time.sleep(0.1)
            assert not failed
            for id in rt_id:
                assert id
            _log.info("RUNTIMES:{}".format(rt_id))
            _log.analyze("TESTRUN", "+ IDS", {'waited': 0.1*i})
            failed = True
            # Try 10 times waiting for storage to be connected
            for i in range(10):
                _log.info("-----------------Round {}-----------------".format(i))
                count=[0]*len(rt)
                try:
                    caps=[0] * len(rt)
                    for j in range(len(rt)):
                        caps[j] = request_handler.get_index(rt[j], "node/capabilities/calvinsys.native.python-json")['result']
                        for k in range(len(rt)):
                            count[k] = count[k] + caps[j].count(rt_id[k])
                    _log.info("\n\trt_ids={}\n\tcount={}\n\tcaps0={}\n\tcaps1={}\n\tcaps2={}\n\tcaps3={}\n\tcaps4={}\n\tcaps5={}".format(rt_id, count, caps[0], caps[1], caps[2], caps[3], caps[4], caps[5]))
                    if all(x>=4 for x in count):
                        failed = False
                        break
                    else:
                        time.sleep(0.2)
                except Exception as err:
                    _log.error("exception from request_handler.get_index, err={}".format(err))
                    time.sleep(0.1)
            assert not failed

            #Loop through all runtimes and check that they can lookup the nodename of all other runtimes
            try:
                for runtime in rt:
                    for rt_attribute in rt_attributes:
                        node_name = rt_attribute['indexed_public']['node_name']
                        _log.debug("get_index node_name={} from rt={}".format(node_name, runtime))
                        response = request_handler.get_index(runtime, format_index_string(['node_name', node_name]))
                        _log.info("\tresponse={}".format(response))
                        assert(response)
                storage_verified = True
            except Exception as err:
                _log.error("Exception err={}".format(err))
                raise
        else:
            _log.info("Storage has already been verified")

###################################
#   Signature related tests
###################################

    @pytest.mark.slow
    def testSecurity_deploy_and_migrate(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        try:
            rt0_id = request_handler.get_node_id(rt[0])
            rt1_id = request_handler.get_node_id(rt[1])
            rt2_id = request_handler.get_node_id(rt[2])
            rt3_id = request_handler.get_node_id(rt[3])
            rt4_id = request_handler.get_node_id(rt[4])
            rt5_id = request_handler.get_node_id(rt[5])
        except Exception as err:
            _log.error("Failed to fetch runtime ids, err={}".format(err))
            raise
        time.sleep(1)
        try:
            self.verify_storage()
        except Exception as err:
            _log.error("Failed storage verification, err={}".format(err))
            raise
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(orig_application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user3", "password": "pass3"}})
            result = request_handler.deploy_application(rt[2], "test_script", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed to deploy script")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of script, no use to verify if requirements fulfilled")
        time.sleep(2)

        #Log actor ids:
        _log.info("Actors id:s:\n\tsrc id={}\n\tsum={}\n\tsnk={}".format(result['actor_map']['test_script:src'],
                                                                        result['actor_map']['test_script:sum'],
                                                                        result['actor_map']['test_script:snk']))


        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_script:src'] in actors[2]
        assert result['actor_map']['test_script:sum'] in actors[2]
        assert result['actor_map']['test_script:snk'] in actors[2]
        time.sleep(1)
        try:
            actual = request_handler.report(rt[2], result['actor_map']['test_script:snk'])
        except Exception as err:
            _log.error("Failed to report from runtime 2, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 5

        #Migrate snk actor to rt1
        time.sleep(2)
        _log.info("Let's migrate actor {} from runtime {}(rt2) to runtime {}(rt1)".format(rt2_id, result['actor_map']['test_script:snk'], rt1_id))
        try:
            request_handler.migrate(rt[2], result['actor_map']['test_script:snk'], rt1_id)
        except Exception as err:
            _log.error("Failed to send first migration request to runtime 2, err={}".format(err))
            raise
        time.sleep(3)
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_script:src'] in actors[2]
        assert result['actor_map']['test_script:sum'] in actors[2]
        assert result['actor_map']['test_script:snk'] in actors[1]
        time.sleep(1)
        try:
            actual = request_handler.report(rt[1], result['actor_map']['test_script:snk'])
        except Exception as err:
            _log.error("Failed to report snk values from runtime 1, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 3

        #Migrate src actor to rt3
        time.sleep(1)
        try:
            request_handler.migrate(rt[2], result['actor_map']['test_script:src'], rt3_id)
        except Exception as err:
            _log.error("Failed to send second migration requestfrom runtime 2, err={}".format(err))
            raise
        time.sleep(3)
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_script:src'] in actors[3]
        assert result['actor_map']['test_script:sum'] in actors[2]
        assert result['actor_map']['test_script:snk'] in actors[1]
        time.sleep(1)
        try:
            actual = request_handler.report(rt[1], result['actor_map']['test_script:snk'])
        except Exception as err:
            _log.error("Failed to report snk values from runtime 1, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 3

        time.sleep(1)
        request_handler.delete_application(rt[2], result['application_id'])


