# -*- coding: utf-8 -*-

# Copyright (c) 2015-2019 Ericsson AB
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


import os
import shlex
import subprocess
import time

import pytest
from mock import Mock
import requests

from calvin.utilities import calvinuuid


##################################
# Begin new system setup fixures #
##################################

def _file_dir():
    return os.path.dirname(os.path.realpath(__file__))

def _start_process(cmd):
    args = shlex.split(cmd)
    process = subprocess.Popen(args)
    return process

def _start_actorstore():
    this_dir = _file_dir()
    app_path = os.path.abspath(this_dir + "/calvinservices/actorstore/store_app.py")
    print app_path
    os.putenv("FLASK_APP", app_path)
    return _start_process("flask run --port 4999")

def _stop_actorstore(proc):
    proc.terminate()

def _start_runtime():
    # return _start_process("csruntime -n localhost -l calvinconfig:DEBUG")
    return _start_process("csruntime -n localhost")
    
def _stop_runtime(proc):
    proc.terminate()  


# FIXTURE: file_dir
# Provide the path to the directory where this file resides
# FIXME: Is this too fragile?
@pytest.fixture(scope='module')
def file_dir():
    return _file_dir()


# FIXTURE: working_dir
# Provide path to a temp dir available for the duration of the test module
@pytest.fixture(scope='module')
def working_dir(tmpdir_factory):
    wdir = tmpdir_factory.mktemp('work')
    wdir = str(wdir)
    return wdir    


# FIXTURE: actorstore
# Setup actorstore for the duration of the test module
@pytest.yield_fixture(scope="module")
def actorstore():
    # Setup
    as_proc = _start_actorstore()
    time.sleep(1)
    # Run tests
    yield
    # Teardown
    _stop_actorstore(as_proc)
    
    
# FIXTURE: single_runtime_system
# Setup actorstore and runtime for the duration of the test module
@pytest.yield_fixture(scope="module")
def single_runtime_system(file_dir, working_dir, patch_config):
    # Setup
    rt_proc = _start_runtime()
    as_proc = _start_actorstore()
    # FIXME: Wait for RT to be in listening mode
    time.sleep(2)
        
    # Run tests
    yield
    
    # Teardown
    _stop_actorstore(as_proc)
    _stop_runtime(rt_proc)
    
# FIXTURE: patch_config
# Override this fixture in test modules to patch the calvin.conf file
# before starting the runtime. See test_runscripts for example use
@pytest.fixture(scope='module')
def patch_config(file_dir, working_dir):
    pass
    
    
#
# Methods previously spread over multiple files, copy-pasted, etc.
#    

class _DummyNode:
    def __init__(self):
        self.id = calvinuuid.uuid("NODE")
        self.control_uri = "http://localhost:5001"
        self.pm = Mock()
        self.storage = Mock()
        self.control = Mock()
        # self.attributes = attribute_resolver.AttributeResolver({})

@pytest.fixture(scope='module')
def dummy_node():
    return _DummyNode()

@pytest.fixture(scope='module')
def dummy_peer_node():
    return _DummyNode()         
            
@pytest.fixture(scope='module')
def control_api():
    
    # PATHS
    NODE_PATH = '/node/{}'
    NODE = '/node'
    NODES = '/nodes'
    NODE_ID = '/id'
    ACTOR = '/actor'
    ACTOR_PATH = '/actor/{}'
    ACTORS = '/actors'
    ACTOR_MIGRATE = '/actor/{}/migrate'
    ACTOR_REPLICATE = '/actor/{}/replicate'
    APPLICATION_PATH = '/application/{}'
    APPLICATION_MIGRATE = '/application/{}/migrate'
    ACTOR_PORT = '/actor/{}/port/{}'
    ACTOR_REPORT = '/actor/{}/report'
    APPLICATIONS = '/applications'
    DEPLOY = '/deploy'
    INDEX_PATH_RPL = '/index/{}?root_prefix_level={}'
    INDEX_PATH = '/index/{}'
    STORAGE_PATH = '/storage/{}'

    class ControlAPI(object):
        """docstring for ControlAPI"""
        def __init__(self):
            super(ControlAPI, self).__init__()
        
        # cscontrol, nodecontrol
        def get_node_id(self, host_uri):
            response = requests.get(host_uri + NODE_ID)
            return response.status_code, response.json()

        # cscontrol
        def deploy(self, host_uri, deployable):
            response = requests.post(host_uri + DEPLOY, json=deployable)
            return response.status_code, response.json()

        # # cscontrol, nodecontrol
        # def get_node(self, rt, node_id):
        #     response = requests.get(host_uri + NODE_PATH.format(node_id))
        #     return response.status_code, response.json()
        #
        # # cscontrol
        # def quit(self, rt, method=None):
        #     if method is None:
        #         r = self._delete(rt, timeout, async, NODE)
        #     else:
        #         r = self._delete(rt, timeout, async, NODE_PATH.format(method))
        #     return self.check_response(r)
        #
        
        def get_actor(self, host_uri, actor_id):
            response = requests.get(host_uri + ACTOR_PATH.format(actor_id))
            return response.status_code, response.json()

        def get_actor_report(self, host_uri, actor_id):
            response = requests.get(host_uri + ACTOR_REPORT.format(actor_id))
            return response.status_code, response.json()

        def get_actors(self, host_uri):
            response = requests.get(host_uri + ACTORS)
            return response.status_code, response.json()

        # cscontrol
        def get_applications(self, host_uri):
            response = requests.get(host_uri + APPLICATIONS)
            return response.status_code, response.json()

        # cscontrol
        def get_application(self, host_uri, application_id):
            response = requests.get(host_uri + APPLICATION_PATH.format(application_id))
            return response.status_code, response.json()

        # cscontrol
        def delete_application(self, host_uri, application_id):
            response = requests.delete(host_uri + APPLICATION_PATH.format(application_id))
            # FIXME: Make control api at least return consistent type, if not value
            return response.status_code, None
        
            
        # # cscontrol, utilities.security, utilities.runtime_credentials
        # def get_index(self, rt, index, root_prefix_level=None):
        #     if root_prefix_level is None:
        #         r = self._get(rt, timeout, async, INDEX_PATH.format(index))
        #     else:
        #         r = self._get(rt, timeout, async, INDEX_PATH_RPL.format(index, root_prefix_level))
        #     return self.check_response(r)
    return ControlAPI()
        

##################################
# End new system setup fixures   #
##################################
