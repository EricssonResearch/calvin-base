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
import json
import time

import pytest
import yaml

from mock import Mock
import requests

from calvin.utilities import calvinuuid
import tests.orchestration as orchestration


##################################
# Begin new system setup fixures #
##################################

def _file_dir():
    return os.path.dirname(os.path.realpath(__file__))
    

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
    

def free_ports():
    import socket
    """
    Determines a free port using sockets.
    """
    def _free_socket():
        free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        free_socket.bind(('localhost', 0))
        free_socket.listen(5)
        return free_socket
    
    s1, s2 = _free_socket(), _free_socket()    
    p1, p2 = s1.getsockname()[1], s2.getsockname()[1]    
    # port = free_socket.getsockname()[1]
    s1.close(), s2.close()
    return (p1, p2)
    

    
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
def system_setup(request, file_dir, working_dir, patch_config):
    """
    Setup a test system according to a system config in YAML or JSON and pass 
    the system info to the tests.
    
    The test module must define either 
    - 'system_config_file' to name a config file in 'tests/systems/', or
    - 'system_config' to be a string with the system config
    where the latter is suitable for very simple setups only.
    
    This fixture relies on the tool-suite (csruntime et al.) so it is probably 
    a good idea to make sure that they are tested first.

    This fixture pretty much replaces all previous fixtures and avoids 
    monkeypatching environment etc.    
    """
    system_config_file = getattr(request.module, "system_config_file", None)
    if system_config_file:
        config_file = os.path.join(file_dir, 'tests/systems', system_config_file)
        with open(config_file, 'r') as fp:
            config = yaml.load(fp)
    else:
        system_config = getattr(request.module, "system_config", None)
        if not system_config: 
            pytest.fail("Need system config!")
        config = yaml.load(system_config)    
        
    sysmgr = orchestration.SystemManager(config)

    yield sysmgr.info
    
    sysmgr.teardown()

            
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
