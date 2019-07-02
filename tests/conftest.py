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

from tools.cscompiler import compile_source
from tools.toolsupport import orchestration
from tools.toolsupport.control_client import ControlAPI


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
            self.proto = Mock()
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
    return ControlAPI()


##################################
# End new system setup fixures   #
##################################
