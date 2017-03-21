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
credentials_testdir = os.path.join(homefolder, ".calvin","test_all_security_together_dir")
runtimesdir = os.path.join(credentials_testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")
runtimes_truststore_signing_path = os.path.join(runtimesdir,"truststore_for_signing")
security_testdir = os.path.join(os.path.dirname(__file__), "security_test")
domain_name="test_security_domain"
code_signer_name="test_signer"
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
            shutil.copytree(orig_identity_provider_path, identity_provider_path)
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
        cs.sign_file(actor_CountTimer_path)

        #Create unsigned version of CountTimer actor
        actor_CountTimerUnsigned_path = actor_CountTimer_path.replace(".py", "Unsigned.py") 
        shutil.copy(actor_CountTimer_path, actor_CountTimerUnsigned_path)
        replace_text_in_file(actor_CountTimerUnsigned_path, "CountTimer", "CountTimerUnsigned")

        #Create signed version of Sum actor
        orig_actor_Sum_path = os.path.join(orig_actor_store_path,"std","Sum.py")
        actor_Sum_path = os.path.join(actor_store_path,"std","Sum.py")
        shutil.copy(orig_actor_Sum_path, actor_Sum_path)
        cs.sign_file(actor_Sum_path)

        #Create unsigned version of Sum actor
        actor_SumUnsigned_path = actor_Sum_path.replace(".py", "Unsigned.py") 
        shutil.copy(actor_Sum_path, actor_SumUnsigned_path)
        replace_text_in_file(actor_SumUnsigned_path, "Sum", "SumUnsigned")

        #Create incorrectly signed version of Sum actor
        actor_SumFake_path = actor_Sum_path.replace(".py", "Fake.py") 
        shutil.copy(actor_Sum_path, actor_SumFake_path)
        #Change the class name to SumFake
        replace_text_in_file(actor_SumFake_path, "Sum", "SumFake")
        cs.sign_file(actor_SumFake_path)
        #Now append to the signed file so the signature verification fails
        with open(actor_SumFake_path, "a") as fd:
                fd.write(" ")

        #Create signed version of Sink actor
        orig_actor_Sink_path = os.path.join(orig_actor_store_path,"test","Sink.py")
        actor_Sink_path = os.path.join(actor_store_path,"test","Sink.py")
        shutil.copy(orig_actor_Sink_path, actor_Sink_path)
        cs.sign_file(actor_Sink_path)

        #Create unsigned version of Sink actor
        actor_SinkUnsigned_path = actor_Sink_path.replace(".py", "Unsigned.py") 
        shutil.copy(actor_Sink_path, actor_SinkUnsigned_path)
        replace_text_in_file(actor_SinkUnsigned_path, "Sink", "SinkUnsigned")

        #Sign applications
        cs.sign_file(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
        cs.sign_file(os.path.join(application_store_path, "test_security1_correctlySignedApp_incorrectlySignedActor.calvin"))
        cs.sign_file(os.path.join(application_store_path, "test_security1_incorrectly_signed.calvin"))
        #Now append to the signed file so the signature verification fails
        with open(os.path.join(application_store_path, "test_security1_incorrectly_signed.calvin"), "a") as fd:
                fd.write(" ")

        print "Export Code Signers certificate to the truststore for code signing"
        out_file = cs.export_cs_cert(runtimes_truststore_signing_path)

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
        #Let's use the admin user0 for request_handler 
        request_handler.set_credentials({"user": "user0", "password": "pass0"})

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

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('security', 'domain_name', domain_name)
        rt_conf.set('security', 'certificate_authority_control_uri',"https://%s:5020" % hostname )
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])
        #TODO: securedht has even more stability issues than dht, so may be preferable
        # to use ordinary dht!
#        rt_conf.set('global', 'storage_type', "securedht")
        rt_conf.set('global', 'storage_type', "dht")

        # Runtime 0: Certificate authority, authentication server, authorization server.
        rt0_conf = copy.deepcopy(rt_conf)
#        rt0_conf.set('global','storage_type','local')
        rt0_conf.set('security','enrollment_password',enrollment_passwords[0])
        rt0_conf.set('security', 'control_interface_security', "tls")
        rt0_conf.set('security','certificate_authority','True')
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

        # Runtime 1: local authentication, signature verification, local authorization.
        rt1_conf = copy.deepcopy(rt_conf)
        rt1_conf.set('security','enrollment_password',enrollment_passwords[1])
        rt1_conf.set("security", "security_conf", {
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
        rt1_conf.save("/tmp/calvin5001.conf")

        for i in range(2, NBR_OF_RUNTIMES):
            rt_conf = copy.deepcopy(rt1_conf)
            rt_conf.set('security','enrollment_password',enrollment_passwords[i])
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


        #Start all runtimes
        for i in range(NBR_OF_RUNTIMES):
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
#            rt.append(RT("http://{}:502{}".format(hostname,i)))
            # Wait to be sure that all runtimes has started
            time.sleep(0.1)
#        time.sleep(10)

        request.addfinalizer(self.teardown)


    def teardown(self):
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
            # Try 100 times waiting for storage to be connected
            for i in range(100):
                _log.info("-----------------Round {}-----------------".format(i))
                count=[0]*NBR_OF_RUNTIMES
                try:
                    caps=[0] * NBR_OF_RUNTIMES
                    #Loop through all runtimes to ask them which runtimes they node with calvisys.native.python-json
                    for j in range(NBR_OF_RUNTIMES):
                        caps[j] = request_handler.get_index(rt[j], "node/capabilities/calvinsys.native.python-json")['result']
                        #Add the known nodes to statistics of how many nodes store keys from that node
                        for k in range(NBR_OF_RUNTIMES):
                            count[k] = count[k] + caps[j].count(rt_id[k])
                    _log.info("rt_ids={}\n\tcount={}".format(rt_id, count))
                    for k in range(NBR_OF_RUNTIMES):
                        _log.info("caps{}={}".format(k, caps[k]))
                    #Keys should have spread to atleast 5 other runtimes (or all if there are fewer than 5 runtimes)
                    if all(x>=min(5, NBR_OF_RUNTIMES) for x in count):
                        failed = False
                        break
                    else:
                        time.sleep(0.2)
                except Exception as err:
                    _log.error("exception from request_handler.get_index, err={}".format(err))
                    time.sleep(0.1)
            assert not failed
            try:
                #Loop through all runtimes and make sure they can lookup all other runtimes
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
    def testSecurity_POSITIVE_CorrectlySignedApp_CorrectlySignedActors(self):
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
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[1]
        request_handler.set_credentials({"user": "user0", "password": "pass0"})
        actual = request_handler.report(rt[1], result['actor_map']['test_security1_correctly_signed:snk'])
        print "actual=", actual
        assert len(actual) > 5

        request_handler.delete_application(rt[1], result['application_id'])


    @pytest.mark.slow
    def testSecurity_NEGATIVE_IncorrectlySignedApp(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_incorrectly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(rt[1], "test_security1_incorrectly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")

    @pytest.mark.slow
    def testSecurity_NEGATIVE_CorrectlySignedApp_IncorrectlySignedActor(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctlySignedApp_incorrectlySignedActor.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctlySignedApp_incorrectlySignedActor", content['file'], 
                    credentials={domain_name:{"user": "user1", "password": "pass1"}}, content=content,
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctlySignedApp_incorrectlySignedActor")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctlySignedApp_incorrectlySignedActor, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:src'] in actors[1]
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:sum'] in actors[1]
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'])
        assert len(actual) == 0  # Means that the incorrectly signed actor was not accepted

        request_handler.delete_application(rt[1], result['application_id'])


###################################
#   Policy related tests
###################################

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_SignedActors(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(rt[1], "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt[1], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_Unsigned_Actor(self):
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
            request_handler.set_credentials({"user": "user3", "password": "pass3"})
            result = request_handler.deploy_application(rt[1], "test_security1_unsignedApp_unsignedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_unsignedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt[1], result['application_id'])

    @pytest.mark.slow
    def testSecurity_NEGATIVE_Deny_SignedApp_SignedActor_UnallowedRequirement(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "pass1"})
            result = request_handler.deploy_application(rt[2], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            _log.debug(str(e))
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[2]

        actual = request_handler.report(rt[2], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) == 0  # Means that the actor with unallowed requirements was not accepted

        request_handler.delete_application(rt[2], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Local_Authorization(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(rt[0], "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors[0]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors[0]

        actual = request_handler.report(rt[0], result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt[0], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_External_Authorization(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user2", "password": "pass2"})
            result = request_handler.deploy_application(rt[1], "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors[1]
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors[1]

        actual = request_handler.report(rt[1], result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt[1], result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Migration_When_Denied(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user4", "password": "pass4"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this (all of them should have migrated to rt[2])
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[2]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[2]

        actual = request_handler.report(rt[2], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt[1], result['application_id'])

###################################
#   Control interface authorization 
#   as well as user db management
###################################

    @pytest.mark.slow
    def testSecurity_NEGATIVE_Control_Interface_Authorization(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user6", "password": "pass6"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'],
                                                        content=content,
                                                        check=True,
                                                        timeout=15.0)
        except Timeout as err:
            _log.error("Timeout while trying to deploy application, err={}".format(err))
            raise
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.error("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")

    @pytest.mark.slow
    def testSecurity_POSITIVE_Add_User(self):
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
        users_db=None
        try:
            request_handler.set_credentials({"user": "user0", "password": "pass0"})
            users_db = request_handler.get_users_db(rt[0])
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        if users_db:
            #TODO: seem more efficient to have a dictionary instead of a list of users
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
        try:
            result = request_handler.post_users_db(rt[0], users_db)
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        #Read the users database back again and check if Greta has been added
        try:
            users_db2 = request_handler.get_users_db(rt[0])
        except Exception as e:
            if e.message.startswith("401"):
                _log.exception("Failed to get users_db, err={}".format(e))
                raise
        if not 'user7' in users_db2:
            raise Exception("Failed to update the users_db")


###################################
#   Authentication related tests
###################################

    @pytest.mark.slow
    def testSecurity_NEGATIVE_UnallowedUser(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user_not_allowed", "password": "pass1"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed did not fail for security reasons")  

    @pytest.mark.slow
    def testSecurity_NEGATIVE_IncorrectPassword(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user1", "password": "incorrect_password"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")  

    @pytest.mark.slow
    def testSecurity_POSITIVE_Local_Authentication(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = request_handler.deploy_application(rt[0], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 0.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[0]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[0]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[0]

        time.sleep(1)
        actual = request_handler.report(rt[0], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt[0], result['application_id']) 

    @pytest.mark.slow
    def testSecurity_POSITIVE_External_Authentication(self):
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
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({"user": "user5", "password": "pass5"})
            result = request_handler.deploy_application(rt[1], "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to runtime 5.\n\te={}".format(e))
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        try:
            actors = fetch_and_log_runtime_actors()
        except Exception as err:
            _log.error("Failed to get actors from runtimes, err={}".format(err))
            raise
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[1]
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[1]

        time.sleep(1)
        actual = request_handler.report(rt[1], result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt[1], result['application_id']) 

#    @pytest.mark.xfail
#    @pytest.mark.slow
#    def testSecurity_POSITIVE_RADIUS_Authentication(self):
#        _log.analyze("TESTRUN", "+", {})
#        global rt
#        global request_handler
#        global security_testdir
#
#        try:
#            self.verify_storage()
#        except Exception as err:
#            _log.error("Failed storage verification, err={}".format(err))
#            raise
#
#        result = {}
#        try:
#            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
#            if not content:
#                raise Exception("Failed finding script, signature and cert, stopping here")
#            request_handler.set_credentials({"user": "user5", "password": "pass5"})
#            result = request_handler.deploy_application(rt[3], "test_security1_correctly_signed", content['file'], 
#                        content=content,
#                        check=True)
#        except Exception as e:
#            if isinstance(e, Timeout):
#                raise Exception("Can't connect to RADIUS server. Have you started a RADIUS server?")
#            elif e.message.startswith("401"):
#                raise Exception("Failed security verification of app test_security1_correctly_signed")
#            _log.exception("Test deploy failed")
#            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
#        time.sleep(2)
#
#        # Verify that actors exist like this
#        try:
#            actors = fetch_and_log_runtime_actors()
#        except Exception as err:
#            _log.error("Failed to get actors from runtimes, err={}".format(err))
#            raise
#        actors = fetch_and_log_runtime_actors()
#        assert result['actor_map']['test_security1_correctly_signed:src'] in actors[3]
#        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors[3]
#        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors[3]
#
#        actual = request_handler.report(rt[3], result['actor_map']['test_security1_correctly_signed:snk'])
#        assert len(actual) > 5
#
#        request_handler.delete_application(rt[3], result['application_id'])
