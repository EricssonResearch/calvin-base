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
    import pprint
    global rt
    # Verify that actors exist like this
    actors=[]
    #Use admins credentials to access the control interface
    request_handler.set_credentials({"user": "user0", "password": "pass0"})
    for runtime in rt:
        actors.append(request_handler.get_actors(runtime))
    for i in range(0,NBR_OF_RUNTIMES):
        _log.info("\n\trt{} actors={}".format(i, actors[i]))
    return actors

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

        print "Trying to create a new test domain configuration."
        ca = certificate_authority.CA(domain=domain_name, commonName="testdomain CA", security_dir=credentials_testdir)
#
        print "Copy CA cert into truststore of runtimes folder"
        ca.export_ca_cert(runtimes_truststore)
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
        #   The following is less than optimal if multiple CA certs exist
        ca_cert_path = os.path.join(truststore_dir, os.listdir(truststore_dir)[0])
        request_handler = RequestHandler(verify=ca_cert_path)
        #Generate credentials, create CSR, sign with CA and import cert for all runtimes
        enrollment_passwords=[]
        for rt_attribute in rt_attributes_cpy:
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
        rt_conf.set('security', 'domain_name', domain_name)
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])
        rt_conf.set('global', 'storage_type', "securedht")

        for i in range(NBR_OF_RUNTIMES):
            rt_conf.set('security','enrollment_password',enrollment_passwords[i])
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
            rt.append(RT("http://{}:{}".format(hostname,5020+i)))
            time.sleep(0.2)
        time.sleep(2)
        _log.info("------------------------------------------------")
        for i in range(NBR_OF_RUNTIMES):
            _log.info("rt[{}] = {}".format(i,  runtimes[i].node_id))
        _log.info("------------------------------------------------")

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


    def verify_storage(self):
        global rt
        global request_handler
        global storage_verified
        _log.info("storage_verified={}".format(storage_verified))
        if not storage_verified:
            _log.info("Let's verify storage, rt={}".format(rt))
            rt_id=[None]*NBR_OF_RUNTIMES
            failed = True
            # Try 30 times waiting for control API to be up and running
            for i in range(30):
                try:
                    for j in range(NBR_OF_RUNTIMES):
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
            try:
                #Loop through all runtimes and make sure they can lookup all other runtimes
                for runtime in rt:
                    for rt_attribute in rt_attributes:
                        node_name = rt_attribute['indexed_public']['node_name']
                        response = request_handler.get_index(runtime, format_index_string(['node_name', node_name]))
                        _log.info("\tresponse={}".format(response))
                        assert(response)
                storage_verified = True
            except Exception as err:
                _log.error("Exception when trying to lookup index={} from rt={},  err={}".format(format_index_string(['node_name', node_name]), runtime.control_uri, err))
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
            rt0_id = request_handler.get_node_id(rt[0])
            rt1_id = request_handler.get_node_id(rt[1])
        except Exception as err:
            _log.error("Failed to fetch runtime ids, err={}".format(err))
            raise
        time.sleep(1)
        start = time.time()
        try:
            self.verify_storage()
        except Exception as err:
            _log.error("Failed storage verification, err={}".format(err))
            raise
        time_to_verify_storaget = time.time()-start

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
        time.sleep(2)
        #Log actor ids:
        _log.info("Actors id:s:\n\tsrc id={}\n\tsum={}\n\tsnk={}".format(result['actor_map']['test_security1_unsignedApp_unsignedActors:src'],
                                                                        result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'],
                                                                        result['actor_map']['test_security1_unsignedApp_unsignedActors:snk']))


        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
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

        #Migrate snk actor to rt1
        time.sleep(2)
        _log.info("Let's migrate actor {} from runtime {}(rt0) to runtime {}(rt1)".format(rt0_id, result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'], rt1_id))
        try:
            request_handler.migrate(rt[0], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'], rt1_id)
        except Exception as err:
            _log.error("Failed to send first migration request to runtime 0, err={}".format(err))
            raise
        time.sleep(3)
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[1]
        time.sleep(1)
        try:
            actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        except Exception as err:
            _log.error("Failed to report snk values from runtime 1, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 3

        #Migrate src actor to rt3
        time.sleep(1)
        try:
            request_handler.migrate(rt[0], result['actor_map']['test_security1_unsignedApp_unsignedActors:src'], rt1_id)
        except Exception as err:
            _log.error("Failed to send second migration requestfrom runtime 0, err={}".format(err))
            raise
        time.sleep(3)
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[1]
        time.sleep(1)
        try:
            actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        except Exception as err:
            _log.error("Failed to report snk values from runtime 1, err={}".format(err))
            raise
        _log.info("actual={}".format(actual))
        assert len(actual) > 3
        _log.info("\n\t----------------------------"
                  "\n\tTotal time to verify storage is {} seconds"
                  "\n\tTotal time of entire (including storage verification) is {} seconds"
                  "\n\t----------------------------".format(time_to_verify_storaget, time.time()-start))

        time.sleep(1)
        request_handler.delete_application(rt[0], result['application_id'])


