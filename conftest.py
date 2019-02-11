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

@pytest.fixture(scope='module')
def start_process():
    """
    Provides function returning process handle to new process given by cmd (string or list).
    Usage: e.g. start_process("csruntime -n localhost")
    """
    def _start_process(cmd):
        if isinstance(cmd, basestring):
            cmd = shlex.split(cmd)
        process = subprocess.Popen(cmd)
        return process
    return _start_process

@pytest.fixture(scope='module')
def start_actorstore(start_process):
    """
    Provides convenience function returning process handle to new actorstore process.
    Usage: start_actorstore()
    """    
    def _start_actorstore():
        app_path = os.path.abspath(_file_dir() + "/calvinservices/actorstore/store_app.py")
        os.putenv("FLASK_APP", app_path)
        return start_process("flask run --port 4999")
    return _start_actorstore

@pytest.fixture(scope='module')
def start_runtime(start_process):
    """
    Provides convenience function returning process handle to new runtime process.
    Usage: start_runtime()
    """
    def _start_runtime():
        # return _start_process("csruntime -n localhost -l calvinconfig:DEBUG")
        return start_process("csruntime -n localhost")
    return _start_runtime
    
@pytest.fixture(scope='module')
def start_registry(start_process):
    """
    Provides convenience function returning process handle to new registry process.
    Usage: start_registry()
    """
    def _start_registry():
        os.putenv("FLASK_APP", "calvinservices/registry/registry_app.py")
        return start_process("flask run --port 4998")
    return _start_registry

@pytest.fixture
def execute_cmd_check_output():
    """
    Provides function returning output on completion of cmd (string or list).
    Usage: e.g. start_process("csdocs io.Print")
    """
    def _execute_cmd(cmd):
        if isinstance(cmd, basestring):
            cmd = shlex.split(cmd)
        res = subprocess.check_output(cmd)
        return res.strip()
    return _execute_cmd

# FIXTURE: file_dir
# Provide the path to the directory where this file resides
# FIXME: Is this too fragile?
@pytest.fixture(scope='module')
def file_dir():
    """
    Return the POSIX path of the root dir as a string.  
    FIXME: Fragile, depends on location of this file.
    """
    return _file_dir()

# FIXTURE: working_dir
@pytest.fixture(scope='module')
def working_dir(tmpdir_factory):
    """Return string with POSIX path to temp dir (module scope)"""
    wdir = tmpdir_factory.mktemp('work')
    wdir = str(wdir)
    return wdir    

@pytest.yield_fixture(scope="module")
def remote_registry(start_registry):
    """
    Setup registry service for the duration of the test module and 
    guarantee teardown afterwards (yield fixture). 
    FIXME: registry uri is hardcoded to "http://localhost:4998"
    """
    # Setup
    reg_proc = start_registry()
    time.sleep(1)
    # Run tests
    yield
    # Teardown
    reg_proc.terminate()

# FIXTURE: actorstore
@pytest.yield_fixture(scope="module")
def actorstore(start_actorstore):
    """
    Setup actorstore for the duration of the test module and 
    guarantee teardown afterwards (yield fixture). 
    FIXME: actorstore uri is hardcoded to "http://localhost:4999"
    """
    # Setup
    as_proc = start_actorstore()
    time.sleep(1)
    # Run tests
    yield
    # Teardown
    as_proc.terminate()
    
    
# FIXTURE: single_runtime_system
@pytest.yield_fixture(scope="module")
def single_runtime_system(file_dir, working_dir, patch_config, start_actorstore, start_runtime):
    """
    Setup actorstore and runtime for the duration of the test module and
    guarantee teardown afterwards (yield fixture).
    Runtime defaults to local (internal) registry.
    FIXME: actorstore uri is hardcoded to "http://localhost:4999"
    FIXME: runtime uri is hardcoded to "http://localhost:5001"
    """
    # Setup
    rt_proc = start_runtime()
    as_proc = start_actorstore()
    # FIXME: Wait for RT to be in listening mode
    time.sleep(2)
        
    # Run tests
    yield
    
    # Teardown
    rt_proc.terminate()
    as_proc.terminate()
    
# FIXTURE: patch_config
@pytest.fixture(scope='module')
def patch_config(file_dir, working_dir):
    """
    Override this fixture in test modules to patch the calvin.conf file
    before starting the runtime. See test_runscripts.py for example use.
    """
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
        self.attributes = Mock()

@pytest.fixture(scope='module')
def dummy_node():
    """
    A dummy node to pass in when unittesting classes that needs a runtime node.
    FIXME: Somehow parametrize this to return any number of nodes and drop dummy_peer_node
    """
    return _DummyNode()

@pytest.fixture(scope='module')
def dummy_peer_node():
    """
    Another dummy node to pass in when unittesting classes that needs a runtime node.
    """
    return _DummyNode()         
            
@pytest.fixture(scope='module')
def control_api():
    """
    Provides a simple way to access the control API of a runtime over HTTP.
    Usage: e.g. control_api.get_node_id("http://localhost:5001")
    It faithfully reflects the flaws of the control API so check source for 
    return value format.
    """
    
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
        def quit(self, host_uri, method=None):
            if method is None:
                response = requests.delete(host_uri + NODE)
            else:
                response = requests.delete(host_uri + NODE_PATH.format(method))
            return response.status_code, None
        
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
