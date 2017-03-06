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
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

homefolder = get_home()
credentials_testdir = os.path.join(homefolder, ".calvin","test_securedht")
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


try:
    ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
except:
    import socket
    # If this fails add hostname to the /etc/hosts file for 127.0.0.1
    ip_addr = socket.gethostbyname(socket.gethostname())
    hostname = socket.gethostname()

rt=[]
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
        global rt
        global request_handler
        try:
            shutil.rmtree(credentials_testdir)
        except Exception as err:
            print "Failed to remove old tesdir, err={}".format(err)
            pass
        try:
            os.makedirs(credentials_testdir)
            os.makedirs(runtimesdir)
            os.makedirs(runtimes_truststore)
            os.makedirs(runtimes_truststore_signing_path)
            os.makedirs(actor_store_path)
            os.makedirs(os.path.join(actor_store_path,"test"))
            shutil.copy(os.path.join(orig_actor_store_path,"test","__init__.py"), os.path.join(actor_store_path,"test","__init__.py"))
            os.makedirs(os.path.join(actor_store_path,"std"))
            shutil.copy(os.path.join(orig_actor_store_path,"std","__init__.py"), os.path.join(actor_store_path,"std","__init__.py"))
            shutil.copytree(orig_application_store_path, application_store_path)
            filelist = [ f for f in os.listdir(application_store_path) if f.endswith(".sign.93d58fef") ]
            for f in filelist:
                    os.remove(os.path.join(application_store_path,f))
            shutil.copytree(os.path.join(security_testdir,"identity_provider"),identity_provider_path)
        except Exception as err:
            _log.error("Failed to create test folder structure, err={}".format(err))
            print "Failed to create test folder structure, err={}".format(err)
            raise

        print "Trying to create a new test application/actor signer."
        cs = code_signer.CS(organization="testsigner", commonName="signer", security_dir=credentials_testdir)

        #Create signed version of CountTimer actor
        orig_actor_CountTimer_path = os.path.join(orig_actor_store_path,"std","CountTimer.py")
        actor_CountTimer_path = os.path.join(actor_store_path,"std","CountTimer.py")
        shutil.copy(orig_actor_CountTimer_path, actor_CountTimer_path)
#        cs.sign_file(actor_CountTimer_path)

        #Create unsigned version of CountTimer actor
        actor_CountTimerUnsigned_path = actor_CountTimer_path.replace(".py", "Unsigned.py") 
        shutil.copy(actor_CountTimer_path, actor_CountTimerUnsigned_path)
        replace_text_in_file(actor_CountTimerUnsigned_path, "CountTimer", "CountTimerUnsigned")

        #Create signed version of Sum actor
        orig_actor_Sum_path = os.path.join(orig_actor_store_path,"std","Sum.py")
        actor_Sum_path = os.path.join(actor_store_path,"std","Sum.py")
        shutil.copy(orig_actor_Sum_path, actor_Sum_path)
#        cs.sign_file(actor_Sum_path)

        #Create unsigned version of Sum actor
        actor_SumUnsigned_path = actor_Sum_path.replace(".py", "Unsigned.py") 
        shutil.copy(actor_Sum_path, actor_SumUnsigned_path)
        replace_text_in_file(actor_SumUnsigned_path, "Sum", "SumUnsigned")

        #Create incorrectly signed version of Sum actor
#        actor_SumFake_path = actor_Sum_path.replace(".py", "Fake.py") 
#        shutil.copy(actor_Sum_path, actor_SumFake_path)
#        #Change the class name to SumFake
#        replace_text_in_file(actor_SumFake_path, "Sum", "SumFake")
#        cs.sign_file(actor_SumFake_path)
#        #Now append to the signed file so the signature verification fails
#        with open(actor_SumFake_path, "a") as fd:
#                fd.write(" ")

        #Create signed version of Sink actor
        orig_actor_Sink_path = os.path.join(orig_actor_store_path,"test","Sink.py")
        actor_Sink_path = os.path.join(actor_store_path,"test","Sink.py")
        shutil.copy(orig_actor_Sink_path, actor_Sink_path)
#        cs.sign_file(actor_Sink_path)

        #Create unsigned version of Sink actor
        actor_SinkUnsigned_path = actor_Sink_path.replace(".py", "Unsigned.py") 
        shutil.copy(actor_Sink_path, actor_SinkUnsigned_path)
        replace_text_in_file(actor_SinkUnsigned_path, "Sink", "SinkUnsigned")

        #Sign applications
#        cs.sign_file(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
#        cs.sign_file(os.path.join(application_store_path, "test_security1_correctlySignedApp_incorrectlySignedActor.calvin"))
#        cs.sign_file(os.path.join(application_store_path, "test_security1_incorrectly_signed.calvin"))
#        #Now append to the signed file so the signature verification fails
#        with open(os.path.join(application_store_path, "test_security1_incorrectly_signed.calvin"), "a") as fd:
#                fd.write(" ")

#        print "Export Code Signers certificate to the truststore for code signing"
#        out_file = cs.export_cs_cert(runtimes_truststore_signing_path)

        print "Trying to create a new test domain configuration."
        ca = certificate_authority.CA(domain=domain_name, commonName="testdomain CA", security_dir=credentials_testdir)
#
        print "Copy CA cert into truststore of runtimes folder"
        ca.export_ca_cert(runtimes_truststore)
        #Define the runtime attributes
        rt0_attributes={'indexed_public':
                  {'owner':{'organization': domain_name, 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'CA'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}}
        rt1_attributes={'indexed_public':
                  {'owner':{'organization': domain_name, 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}}
        rt2_attributes={'indexed_public':
                  {'owner':{'organization': domain_name, 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'otherStreet', 'streetNumber': 1}}}
        rt3_attributes={'indexed_public':
                  {'owner':{'organization': domain_name, 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode3'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}}
        rt4_attributes={'indexed_public':
                  {'owner':{'organization': domain_name, 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode4'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}}
        rt5_attributes={'indexed_public':
                  {'owner':{'organization': domain_name, 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode5'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}}
        rt_attributes=[]
        rt_attributes.append(deepcopy(rt0_attributes))
        rt_attributes.append(deepcopy(rt1_attributes))
        rt_attributes.append(deepcopy(rt2_attributes))
        rt_attributes.append(deepcopy(rt3_attributes))
        rt_attributes.append(deepcopy(rt4_attributes))
        rt_attributes.append(deepcopy(rt5_attributes))
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
        for rt_attribute in rt_attributes:
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
        #Let's hash passwords in users.json file (the runtimes will try to do this
        # but they will all try to do it at the same time, so it will be overwritten
        # multiple times and the first test will always fail)
#        self.arp = FileAuthenticationRetrievalPoint(identity_provider_path)
#        self.arp.check_stored_users_db_for_unhashed_passwords()

        #The policy allows access to control interface for everyone, for more advanced rules
        # it might be appropriate to run set_credentials for request_handler, e.g.,
        #  request_handler.set_credentials({domain_name:{"user": "user2", "password": "pass2"}})

        rt_conf = copy.deepcopy(_conf)
#        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
#        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('security', 'domain_name', domain_name)
#        rt_conf.set('security', 'certificate_authority_control_uri',"https://%s:5020" % hostname )
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])
        rt_conf.set('global', 'storage_type', "securedht")

        # Runtime 0: local authentication, signature verification, local authorization.
        # Primarily acts as Certificate Authority for the domain
        rt0_conf = copy.deepcopy(rt_conf)
#        rt0_conf.set('security','enrollment_password',enrollment_passwords[0])
        #The csruntime certificate requests assumes TLS for the control interface
#        rt0_conf.set('security', 'control_interface_security', "tls")
#        rt0_conf.set('security','certificate_authority','True')
#        rt0_conf.set("security", "security_conf", {
#                        "comment": "Certificate Authority",
#                        "authentication": {
#                            "procedure": "local",
#                            "identity_provider_path": identity_provider_path
#                        },
#                        "authorization": {
#                            "procedure": "local",
#                            "policy_storage_path": policy_storage_path
#                        }
#                    })
        rt0_conf.save("/tmp/calvin5000.conf")

        # Runtime 1: local authentication, signature verification, local authorization.
        rt1_conf = copy.deepcopy(rt_conf)
#        rt1_conf.set('security','enrollment_password',enrollment_passwords[1])
#        rt1_conf.set("security", "security_conf", {
#                        "comment": "Local authentication, local authorization",
#                        "authentication": {
#                            "procedure": "local",
#                            "identity_provider_path": identity_provider_path
#                        },
#                        "authorization": {
#                            "procedure": "local",
#                            "policy_storage_path": policy_storage_path
#                        }
#                    })
        rt1_conf.save("/tmp/calvin5001.conf")

        # Runtime 2: local authentication, signature verification, local authorization.
        # Can also act as authorization server for other runtimes.
        # Other street compared to the other runtimes
        rt2_conf = copy.deepcopy(rt_conf)
#        rt2_conf.set('security','enrollment_password',enrollment_passwords[2])
#        rt2_conf.set("security", "security_conf", {
#                        "comment": "Local authentication, local authorization",
#                        "authentication": {
#                            "procedure": "local",
#                            "identity_provider_path": identity_provider_path
#                        },
#                        "authorization": {
#                            "procedure": "local",
#                            "policy_storage_path": policy_storage_path,
#                            "accept_external_requests": True
#                        }
#                    })
        rt2_conf.save("/tmp/calvin5002.conf")

        # Runtime 3: external authentication (RADIUS), signature verification, local authorization.
        rt3_conf = copy.deepcopy(rt_conf)
#        rt3_conf.set('security','enrollment_password',enrollment_passwords[3])
#        rt3_conf.set("security", "security_conf", {
#                        "comment": "RADIUS authentication, local authorization",
#                        "authentication": {
#                            "procedure": "radius", 
#                            "server_ip": "localhost", 
#                            "secret": "elxghyc5lz1_passwd"
#                        },
#                        "authorization": {
#                            "procedure": "local",
#                            "policy_storage_path": policy_storage_path
#                        }
#                    })
        rt3_conf.save("/tmp/calvin5003.conf")

        # Runtime 4: local authentication, signature verification, external authorization (runtime 2).
        rt4_conf = copy.deepcopy(rt_conf)
#        rt4_conf.set('security','enrollment_password',enrollment_passwords[4])
#        rt4_conf.set("security", "security_conf", {
#                        "comment": "Local authentication, external authorization",
#                        "authentication": {
#                            "procedure": "local",
#                            "identity_provider_path": identity_provider_path
#                        },
#                        "authorization": {
#                            "procedure": "external"
#                        }
#                    })
        rt4_conf.save("/tmp/calvin5004.conf")

        # Runtime 5: external authentication (runtime 1), signature verification, local authorization.
        rt5_conf = copy.deepcopy(rt_conf)
#        rt5_conf.set('global','storage_type','proxy')
#        rt5_conf.set('global','storage_proxy',"calvinip://%s:5000" % ip_addr )
#        rt5_conf.set('security','enrollment_password',enrollment_passwords[5])
#        rt5_conf.set("security", "security_conf", {
#                        "comment": "Local authentication, external authorization",
#                        "authentication": {
#                            "procedure": "external",
#                            "server_uuid": runtimes[1].node_id
#                        },
#                        "authorization": {
#                            "procedure": "local",
#                            "policy_storage_path": policy_storage_path
#                        }
#                    })
        rt5_conf.save("/tmp/calvin5005.conf")

        #Start all runtimes
        for i in range(len(rt_attributes_cpy)):
            _log.info("Starting runtime {}".format(i))
            try:
                logfile = _config_pytest.getoption("logfile")+"500{}".format(i)
                outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
                if outfile == logfile:
                    outfile = None
            except:
                logfile = None
                outfile = None
            csruntime(hostname, port=5000+i, controlport=5020+i, attr=rt_attributes_cpy[i],
                       loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                       configfile="/tmp/calvin500{}.conf".format(i))
#            rt.append(RT("https://{}:502{}".format(hostname, i)))
            rt.append(RT("http://{}:502{}".format(hostname,i)))
            # Wait to be sure that all runtimes has started
            time.sleep(1)
        time.sleep(10)

        request.addfinalizer(self.teardown)


    def teardown(self):
        global rt
        global request_handler
        for runtime in rt:
            request_handler.quit(runtime)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        os.system("pkill -9 -f 'csruntime -n %s -p 5000'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5001'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5002'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5003'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5004'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5005'" % (hostname,))
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
            # Try 100 times waiting for storage to be connected
            for i in range(100):
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
            try:
                _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})
                assert request_handler.get_index(rt[0], format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'CA'}]))
                _log.analyze("TESTRUN", "+ RT0 INDEX", {})
                assert request_handler.get_index(rt[1], format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
                _log.analyze("TESTRUN", "+ RT1 INDEX", {})
                assert request_handler.get_index(rt[2], format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
                _log.analyze("TESTRUN", "+ RT2 INDEX", {})
                assert request_handler.get_index(rt[3], format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode3'}]))
                _log.analyze("TESTRUN", "+ RT3 INDEX", {})
                assert request_handler.get_index(rt[4], format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode4'}]))
                _log.analyze("TESTRUN", "+ RT4 INDEX", {})
                assert request_handler.get_index(rt[5], format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode5'}]))
                _log.analyze("TESTRUN", "+ RT5 INDEX", {})

                storage_verified = True
            except Exception as err:
                _log.error("Exception err={}".format(err))
                raise
        else:
            _log.info("Storage has already been verified")





###################################
#   Policy related tests
###################################

    @pytest.mark.slow
    def testSecurity_deploy_and_migrate(self):
        _log.analyze("TESTRUN", "+", {})
        global rt
        global request_handler
        global security_testdir
        try:
            self.verify_storage()
        except Exception as err:
            _log.error("Failed storage verification, err={}".format(err))
            raise
        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_unsignedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user3", "password": "pass3"}})
            result = request_handler.deploy_application(rt[2], "test_security1_unsignedApp_unsignedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed to deploy test_security1_unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_unsignedActors, no use to verify if requirements fulfilled")
        time.sleep(2)
        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[2]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[2]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[2]
        actual = request_handler.report(rt[2], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        _log.info("actual={}".format(actual))
        assert len(actual) > 5

        #Migrate snk actor to rt1
        time.sleep(1)
        request_handler.migrate(rt[2], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'], request_handler.get_node_id(rt[1]))
        time.sleep(1)
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[2]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[2]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[1]
        _log.info("kommer hit")
        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        _log.info("actual={}".format(actual))
        assert len(actual) > 3

        #Migrate src actor to rt3
        time.sleep(1)
        request_handler.migrate(rt[2], result['actor_map']['test_security1_unsignedApp_unsignedActors:src'], request_handler.get_node_id(rt[3]))
        time.sleep(1)
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[3]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[2]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[1]
        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        _log.info("actual={}".format(actual))
        assert len(actual) > 3

        request_handler.delete_application(rt[2], result['application_id'])


