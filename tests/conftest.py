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
import shutil
import time
import uuid

import pytest
import yaml
from unittest.mock import Mock
import requests

from calvinservices.csparser.cscompiler import compile_source
from calvin.Tools import orchestration


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
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        res = subprocess.check_output(cmd, encoding='utf-8')
        return res.strip()
    return _execute_cmd


# Provide the path to the directory where this file resides
# FIXME: Is this too fragile?
@pytest.fixture(scope='module')
def tests_dir():
    """
    Return the POSIX path to the tests/ dir as a string.  
    FIXME: Fragile, depends on location of this file.
    """
    return _file_dir()


@pytest.fixture(scope='module')
def working_dir(tmpdir_factory, tests_dir):
    """
    Return string with POSIX path to temp dir (module scope)
    """
    wdir = tmpdir_factory.mktemp('work')
    wdir = str(wdir)
    return wdir   
    
    
@pytest.fixture()
def dummy_node():
    """
    A dummy node to pass in when unittesting classes that needs a runtime node.
    """
    class _DummyNode:
        def __init__(self):
            self.id = str(uuid.uuid4())
            self.control_uri = "http://localhost:5001"
            self.pm = Mock()
            self.storage = Mock()
            self.control = Mock()
            self.attributes = Mock()
    return _DummyNode()


@pytest.fixture(scope='module')
def system_setup(request, tests_dir, working_dir):
    """
    Setup a test system according to a system config in YAML and pass 
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
        config_file = os.path.join(tests_dir, 'systems', system_config_file)
        with open(config_file, 'r') as fp:
            system_config = fp.read()
    else:
        system_config = getattr(request.module, "system_config", None)
        if not system_config: 
            pytest.fail("Need system config!")
    system_config = system_config.format(working_dir=working_dir)        
    config = yaml.load(system_config, Loader=yaml.SafeLoader)    
        
    sysmgr = orchestration.SystemManager(config, working_dir)

    yield sysmgr.info
    
    sysmgr.teardown()

@pytest.fixture(scope='module')
def deploy_app(control_api):
    """
    Return an application deployer instance
    Usage: app_info = deploy_app(rt_uri, script, name)
    """
    def _deploy_app(rt_uri, script, name, actorstore_uri):
        deployable, issuetracker = compile_source(script, name, actorstore_uri)
        assert issuetracker.errors() == []
        # Deploy to rt1
        status, app_info = control_api.deploy(rt_uri, deployable)
        assert status == 200
        # FIXME: Check with app_id instead
        status, applications = control_api.get_applications(rt_uri)
        assert status == 200
        app_id = app_info['application_id']
        assert app_id in applications
        return app_info
    return _deploy_app

    
@pytest.fixture(scope='module')
def destroy_app(control_api):
    """
    Return an application destroyer instance
    Usage: destroy_app(rt_uri, app_info)
    """
    def _destroy_app(rt_uri, app_info):
        app_id = app_info['application_id']
        status, _ = control_api.delete_application(rt_uri, app_id)
        assert status in range(200, 207)
        # FIXME: Check with app_id instead
        status, applications = control_api.get_applications(rt_uri)
        assert status == 200
        assert app_id not in applications
    return _destroy_app

            
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
        # N.B. This queries the RUNTIME at host_uri
        def get_node_id(self, host_uri):
            response = requests.get(host_uri + NODE_ID)
            return response.status_code, response.json()

        # cscontrol
        def deploy(self, host_uri, deployable):
            response = requests.post(host_uri + DEPLOY, json=deployable)
            return response.status_code, response.json()

        # cscontrol
        # N.B. This queries the RUNTIME at host_uri, and may thus fail
        def migrate_actor(self, host_uri, actor_id, reqs):
            response = requests.post(host_uri + ACTOR_MIGRATE.format(actor_id), json=reqs)
            return response.status_code, None

        # cscontrol, nodecontrol
        def get_node(self, host_uri, node_id):
            response = requests.get(host_uri + NODE_PATH.format(node_id))
            return response.status_code, response.json()

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

        # N.B. This queries the RUNTIME at host_uri, and may thus fail, use get_actor to find out where the actor resides
        def get_actor_report(self, host_uri, actor_id):
            response = requests.get(host_uri + ACTOR_REPORT.format(actor_id))
            return response.status_code, response.json()

        # N.B. This queries the RUNTIME at host_uri, and may thus fail, use get_actor to find out where the actor resides
        def get_actors(self, host_uri):
            response = requests.get(host_uri + ACTORS)
            return response.status_code, response.json()

        # cscontrol
        # N.B. This queries the RUNTIME at host_uri
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

        def migrate_application(self, host_uri, app_id, reqs):
            response = requests.post(host_uri + APPLICATION_MIGRATE.format(app_id), json=reqs)
            return response.status_code, None
                    
    return ControlAPI()
        

##################################
# End new system setup fixures   #
##################################
