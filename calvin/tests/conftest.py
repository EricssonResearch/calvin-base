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


##################################
# Begin new system setup fixures #
##################################

def _start_process(cmd):
    args = shlex.split(cmd)
    process = subprocess.Popen(args)
    return process



def _start_actorstore():
    this_dir = file_dir()
    app_path = os.path.abspath(this_dir + "/../../" + "calvinservices/actorstore/store_app.py")
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
    return os.path.dirname(os.path.realpath(__file__))


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

##################################
# End new system setup fixures   #
##################################
