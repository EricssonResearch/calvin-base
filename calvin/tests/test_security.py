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
credentials_testdir = os.path.join(homefolder, ".calvin","test_security_credentials_dir")
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
    # ip_addr = socket.gethostbyname(socket.gethostname())
    hostname = socket.gethostname()


rt0 = None
rt1 = None
rt2 = None
rt3 = None
rt4 = None
request_handler=None

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

@pytest.mark.slow
class TestSecurity(unittest.TestCase):

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        from calvin.Tools.csruntime import csruntime
        from conftest import _config_pytest
        import fileinput
        global rt0
        global rt1
        global rt2
        global rt3
        global rt4
        global request_handler
        try:
            shutil.rmtree(credentials_testdir)
        except Exception as err:
            print "Failed to remove old tesdir, err={}".format(err)
            pass
        try:
            os.mkdir(credentials_testdir)
            os.mkdir(runtimesdir)
            os.mkdir(runtimes_truststore)
            os.mkdir(runtimes_truststore_signing_path)
            os.mkdir(actor_store_path)
            os.mkdir(os.path.join(actor_store_path,"io"))
            shutil.copy(os.path.join(orig_actor_store_path,"io","__init__.py"), os.path.join(actor_store_path,"io","__init__.py"))
            os.mkdir(os.path.join(actor_store_path,"std"))
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

        #Create signed version of StandardOut actor
        orig_actor_StandardOut_path = os.path.join(orig_actor_store_path,"io","StandardOut.py")
        actor_StandardOut_path = os.path.join(actor_store_path,"io","StandardOut.py")
        shutil.copy(orig_actor_StandardOut_path, actor_StandardOut_path)
        cs.sign_file(actor_StandardOut_path)

        #Create unsigned version of StandardOut actor
        actor_StandardOutUnsigned_path = actor_StandardOut_path.replace(".py", "Unsigned.py") 
        shutil.copy(actor_StandardOut_path, actor_StandardOutUnsigned_path)
        replace_text_in_file(actor_StandardOutUnsigned_path, "StandardOut", "StandardOutUnsigned")

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
        rt_attributes=[]
        rt_attributes.append(deepcopy(rt0_attributes))
        rt_attributes.append(deepcopy(rt1_attributes))
        rt_attributes.append(deepcopy(rt2_attributes))
        rt_attributes.append(deepcopy(rt3_attributes))
        rt_attributes.append(deepcopy(rt4_attributes))
        runtimes=[]
        #Initiate Requesthandler with trusted CA cert
        truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT, 
                                                         security_dir=credentials_testdir)
        #   The following is less than optimal if multiple CA certs exist
        ca_cert_path = os.path.join(truststore_dir, os.listdir(truststore_dir)[0])
        request_handler = RequestHandler(verify=ca_cert_path)
        #Generate enrollment passwords for all runtimes
        enrollment_passwords=[]
        for rt_attribute in rt_attributes:
            attributes=AttributeResolver(rt_attribute)
            node_name = attributes.get_node_name_as_str()
            nodeid = calvinuuid.uuid("")
            enrollment_passwords.append(ca.cert_enrollment_add_new_runtime(node_name))

        #Let's hash passwords in users.json file (the runtimes will try to do this
        # but they will all try to do it at the same time, so it will be overwritten
        # multiple times and the first test will always fail)
        self.arp = FileAuthenticationRetrievalPoint(identity_provider_path)
        self.arp.check_stored_users_db_for_unhashed_passwords()

        #The policy allows access to control interface for everyone, for more advanced rules
        # it might be appropriate to run set_credentials for request_handler, e.g.,
        #  request_handler.set_credentials({domain_name:{"user": "user2", "password": "pass2"}})

        rt_conf = copy.deepcopy(_conf)
        rt_conf.set('security', 'runtime_to_runtime_security', "tls")
        rt_conf.set('security', 'control_interface_security', "tls")
        rt_conf.set('security', 'domain_name', domain_name)
        #TODO: remove use of "security_domain_name"
        rt_conf.set('security', 'security_domain_name', domain_name)
        rt_conf.set('security', 'certificate_authority_control_uri',"https://%s:5020" % hostname )
        rt_conf.set('security', 'security_dir', credentials_testdir)
        rt_conf.set('security', 'security_path', credentials_testdir)
        rt_conf.set('global', 'actor_paths', [actor_store_path])

        # Runtime 0: local authentication, signature verification, local authorization.
        # Primarily acts as Certificate Authority for the domain
        rt0_conf = copy.deepcopy(rt_conf)
        rt0_conf.set('security','enrollment_password',enrollment_passwords[0])
        rt0_conf.set('security', 'control_interface_security', "tls")
        rt0_conf.set('security','certificate_authority','True')
        rt0_conf.set("security", "security_conf", {
                        "comment": "Certificate Authority",
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": identity_provider_path
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": policy_storage_path
                        }
                    })
        rt0_conf.save("/tmp/calvin5000.conf")

        try:
            logfile = _config_pytest.getoption("logfile")+"5000"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(hostname, port=5000, controlport=5020, attr=rt0_attributes,
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5000.conf")
        rt0 = RT("https://%s:5020" % hostname)

        #Wait for the CA runtime to start before sending CSR requests
        #TODO: remove the need for this
        time.sleep(5)

        # Runtime 1: local authentication, signature verification, local authorization.
        rt1_conf = copy.deepcopy(rt_conf)
        rt1_conf.set('security','enrollment_password',enrollment_passwords[1])
        rt1_conf.set("security", "security_conf", {
                        "comment": "Local authentication, local authorization",
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": identity_provider_path
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": policy_storage_path
                        }
                    })
        rt1_conf.save("/tmp/calvin5001.conf")

        try:
            logfile = _config_pytest.getoption("logfile")+"5001"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(hostname, port=5001, controlport=5021, attr=rt1_attributes,
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5001.conf")
        rt1 = RT("https://%s:5021" % hostname)


        # Runtime 2: local authentication, signature verification, local authorization.
        # Can also act as authorization server for other runtimes.
        # Other street compared to the other runtimes
        rt2_conf = copy.deepcopy(rt_conf)
        rt2_conf.set('security','enrollment_password',enrollment_passwords[2])
        rt2_conf.set("security", "security_conf", {
                        "comment": "Local authentication, local authorization",
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": identity_provider_path
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": policy_storage_path,
                            "accept_external_requests": True
                        }
                    })
        rt2_conf.save("/tmp/calvin5002.conf")

        try:
            logfile = _config_pytest.getoption("logfile")+"5002"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(hostname, port=5002, controlport=5022, attr=rt2_attributes,
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5002.conf")
        rt2 = RT("https://%s:5022" % hostname)


        # Runtime 3: external authentication (RADIUS), signature verification, local authorization.
        rt3_conf = copy.deepcopy(rt_conf)
        rt3_conf.set('security','enrollment_password',enrollment_passwords[3])
        rt3_conf.set("security", "security_conf", {
                        "comment": "RADIUS authentication, local authorization",
                        "authentication": {
                            "procedure": "radius", 
                            "server_ip": "localhost", 
                            "secret": "elxghyc5lz1_passwd"
                        },
                        "authorization": {
                            "procedure": "local",
                            "policy_storage_path": policy_storage_path
                        }
                    })
        rt3_conf.save("/tmp/calvin5003.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5003"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(hostname, port=5003, controlport=5023, attr=rt3_attributes,
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5003.conf")
        rt3 = RT("https://%s:5023" % hostname)

        # Runtime 4: local authentication, signature verification, external authorization (runtime 2).
        time.sleep(2)
        rt4_conf = copy.deepcopy(rt_conf)
        rt4_conf.set('security','enrollment_password',enrollment_passwords[4])
        rt4_conf.set("security", "security_conf", {
                        "comment": "Local authentication, external authorization",
                        "authentication": {
                            "procedure": "local",
                            "identity_provider_path": identity_provider_path
                        },
                        "authorization": {
                            "procedure": "external"
                        }
                    })
        rt4_conf.save("/tmp/calvin5004.conf")
        try:
            logfile = _config_pytest.getoption("logfile")+"5004"
            outfile = os.path.join(os.path.dirname(logfile), os.path.basename(logfile).replace("log", "out"))
            if outfile == logfile:
                outfile = None
        except:
            logfile = None
            outfile = None
        csruntime(hostname, port=5004, controlport=5024, attr=rt4_attributes,
                   loglevel=_config_pytest.getoption("loglevel"), logfile=logfile, outfile=outfile,
                   configfile="/tmp/calvin5004.conf")
        rt4 = RT("https://%s:5024" % hostname)

        time.sleep(10)  # Wait to be sure that all runtimes has started

        request.addfinalizer(self.teardown)

    def teardown(self):
        global rt0
        global rt1
        global rt2
        global rt3
        global rt4
        global request_handler
        request_handler.quit(rt0)
        request_handler.quit(rt1)
        request_handler.quit(rt2)
        request_handler.quit(rt3)
        request_handler.quit(rt4)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        # They will die eventually (about 5 seconds) in most cases, but this makes sure without wasting time
        os.system("pkill -9 -f 'csruntime -n %s -p 5000'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5001'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5002'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5003'" % (hostname,))
        os.system("pkill -9 -f 'csruntime -n %s -p 5004'" % (hostname,))
        time.sleep(0.2)

    def verify_storage(self):
        global rt0
        global rt1
        global rt2
        global rt3
        global rt4
        global request_handler
        rt0_id = None
        rt1_id = None
        rt2_id = None
        rt3_id = None
        rt4_id = None
        failed = True
        # Try 30 times waiting for control API to be up and running
        for i in range(30):
            try:
                rt0_id = rt0_id or request_handler.get_node_id(rt0)
                rt1_id = rt1_id or request_handler.get_node_id(rt1)
                rt2_id = rt2_id or request_handler.get_node_id(rt2)
                rt3_id = rt3_id or request_handler.get_node_id(rt3)
                rt4_id = rt4_id or request_handler.get_node_id(rt4)
                failed = False
                break
            except:
                time.sleep(0.1)
        assert not failed
        assert rt0_id
        assert rt1_id
        assert rt2_id
        assert rt3_id
        assert rt4_id
        print "RUNTIMES:", rt0_id, rt1_id, rt2_id, rt3_id, rt4_id
        _log.analyze("TESTRUN", "+ IDS", {'waited': 0.1*i})
        failed = True
        # Try 30 times waiting for storage to be connected
        caps0 = []
        caps1 = []
        caps2 = []
        caps3 = []
        caps4 = []
        rt_ids = set([rt0_id, rt1_id, rt2_id, rt3_id, rt4_id])
        for i in range(30):
            try:
                if not (rt0_id in caps0 and rt1_id in caps0 and rt2_id in caps0 and rt3_id in caps0 and rt4_id in caps0):
                    caps0 = request_handler.get_index(rt0, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt0_id in caps1 and rt1_id in caps1 and rt2_id in caps1 and rt3_id in caps1 and rt4_id in caps1):
                    caps1 = request_handler.get_index(rt1, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt0_id in caps2 and rt1_id in caps2 and rt2_id in caps2 and rt3_id in caps2 and rt4_id in caps2):
                    caps2 = request_handler.get_index(rt2, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt0_id in caps3 and rt1_id in caps3 and rt2_id in caps3 and rt3_id in caps3 and rt4_id in caps3):
                    caps3 = request_handler.get_index(rt3, "node/capabilities/calvinsys.native.python-json")['result']
                if not (rt0_id in caps4 and rt1_id in caps4 and rt2_id in caps4 and rt3_id in caps4 and rt4_id in caps4):
                    caps4 = request_handler.get_index(rt4, "node/capabilities/calvinsys.native.python-json")['result']
                if rt_ids <= set(caps0) and rt_ids <= set(caps1) and rt_ids <= set(caps2) and rt_ids <= set(caps3) and rt_ids <= set(caps4):
                    failed = False
                    break
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        assert not failed
        _log.analyze("TESTRUN", "+ STORAGE", {'waited': 0.1*i})
        assert request_handler.get_index(rt0, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'CA'}]))
        _log.analyze("TESTRUN", "+ RT1 INDEX", {})
        assert request_handler.get_index(rt1, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode1'}]))
        _log.analyze("TESTRUN", "+ RT1 INDEX", {})
        assert request_handler.get_index(rt2, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode2'}]))
        _log.analyze("TESTRUN", "+ RT2 INDEX", {})
        assert request_handler.get_index(rt3, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode3'}]))
        _log.analyze("TESTRUN", "+ RT3 INDEX", {})
        assert request_handler.get_index(rt4, format_index_string(['node_name', {'organization': 'org.testexample', 'name': 'testNode4'}]))
        _log.analyze("TESTRUN", "+ RT4 INDEX", {})


###################################
#   Signature related tests
###################################

    @pytest.mark.slow
    def testSecurity_POSITIVE_CorrectlySignedApp_CorrectlySignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user1", "password": "pass1"}})
            result = request_handler.deploy_application(rt1, "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt1)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt1, result['actor_map']['test_security1_correctly_signed:snk'])
        print "actual=", actual
        assert len(actual) > 5

        request_handler.delete_application(rt1, result['application_id'])

    @pytest.mark.slow
    def testSecurity_NEGATIVE_IncorrectlySignedApp(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_incorrectly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user1", "password": "pass1"}})
            result = request_handler.deploy_application(rt1, "test_security1_incorrectly_signed", content['file'], 
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
        global rt1
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctlySignedApp_incorrectlySignedActor.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user1", "password": "pass1"}})
            result = request_handler.deploy_application(rt1, "test_security1_correctlySignedApp_incorrectlySignedActor", content['file'], 
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
        actors = request_handler.get_actors(rt1)
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:src'] in actors
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:sum'] in actors
        assert result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'] in actors

        actual = request_handler.report(rt1, result['actor_map']['test_security1_correctlySignedApp_incorrectlySignedActor:snk'])
        assert len(actual) == 0  # Means that the incorrectly signed actor was not accepted

        request_handler.delete_application(rt1, result['application_id'])


###################################
#   Policy related tests
###################################

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_SignedActors(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user2", "password": "pass2"}})
            result = request_handler.deploy_application(rt2, "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt2)
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors

        actual = request_handler.report(rt2, result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Permit_UnsignedApp_Unsigned_Actor(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_unsignedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user3", "password": "pass3"}})
            result = request_handler.deploy_application(rt2, "test_security1_unsignedApp_unsignedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_unsignedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_unsignedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt2)
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:src'] in actors
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:sum'] in actors
        assert result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'] in actors

        actual = request_handler.report(rt2, result['actor_map']['test_security1_unsignedApp_unsignedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurity_NEGATIVE_Deny_SignedApp_SignedActor_UnallowedRequirement(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user1", "password": "pass1"}})
            result = request_handler.deploy_application(rt2, "test_security1_correctly_signed", content['file'], 
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
        actors = request_handler.get_actors(rt2)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt2, result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) == 0  # Means that the actor with unallowed requirements was not accepted

        request_handler.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_External_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global rt4
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_unsignedApp_signedActors.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user2", "password": "pass2"}})
            result = request_handler.deploy_application(rt4, "test_security1_unsignedApp_signedActors", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_unsignedApp_signedActors")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_unsignedApp_signedActors, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt4)
        assert result['actor_map']['test_security1_unsignedApp_signedActors:src'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:sum'] in actors
        assert result['actor_map']['test_security1_unsignedApp_signedActors:snk'] in actors

        actual = request_handler.report(rt4, result['actor_map']['test_security1_unsignedApp_signedActors:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt4, result['application_id'])

    @pytest.mark.slow
    def testSecurity_POSITIVE_Migration_When_Denied(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global rt4
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user4", "password": "pass4"}})
            result = request_handler.deploy_application(rt2, "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this (all of them should have migrated to rt4)
        actors = request_handler.get_actors(rt4)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt4, result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt2, result['application_id'])

    @pytest.mark.slow
    def testSecurity_NEGATIVE_Control_Interface_Authorization(self):
        _log.analyze("TESTRUN", "+", {})
        global rt2
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user6", "password": "pass6"}})
            result = request_handler.deploy_application(rt2, "test_security1_correctly_signed", content['file'],
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")

###################################
#   Authentication related tests
###################################

    @pytest.mark.slow
    def testSecurity_NEGATIVE_UnallowedUser(self):
        _log.analyze("TESTRUN", "+", {})
        global rt1
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user_not_allowed", "password": "pass1"}})
            result = request_handler.deploy_application(rt1, "test_security1_correctly_signed", content['file'], 
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
        global rt1
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user1", "password": "incorrect_password"}})
            result = request_handler.deploy_application(rt1, "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if e.message.startswith("401"):
                # We were blocked, as we should
                return
            _log.exception("Test deploy failed for non security reasons")

        raise Exception("Deployment of app test_security1_correctly_signed, did not fail for security reasons")  

    #This only works if a properly configured RADIUS server is available on localhost
    @pytest.mark.xfail
    @pytest.mark.slow
    def testSecurity_POSITIVE_RADIUS_Authentication(self):
        _log.analyze("TESTRUN", "+", {})
        global rt3
        global request_handler
        global security_testdir

        self.verify_storage()

        result = {}
        try:
            content = Security.verify_signature_get_files(os.path.join(application_store_path, "test_security1_correctly_signed.calvin"))
            if not content:
                raise Exception("Failed finding script, signature and cert, stopping here")
            request_handler.set_credentials({domain_name:{"user": "user5", "password": "pass5"}})
            result = request_handler.deploy_application(rt3, "test_security1_correctly_signed", content['file'], 
                        content=content,
                        check=True)
        except Exception as e:
            if isinstance(e, Timeout):
                raise Exception("Can't connect to RADIUS server. Have you started a RADIUS server?")
            elif e.message.startswith("401"):
                raise Exception("Failed security verification of app test_security1_correctly_signed")
            _log.exception("Test deploy failed")
            raise Exception("Failed deployment of app test_security1_correctly_signed, no use to verify if requirements fulfilled")
        time.sleep(2)

        # Verify that actors exist like this
        actors = request_handler.get_actors(rt3)
        assert result['actor_map']['test_security1_correctly_signed:src'] in actors
        assert result['actor_map']['test_security1_correctly_signed:sum'] in actors
        assert result['actor_map']['test_security1_correctly_signed:snk'] in actors

        actual = request_handler.report(rt3, result['actor_map']['test_security1_correctly_signed:snk'])
        assert len(actual) > 5

        request_handler.delete_application(rt3, result['application_id'])
