import os
import shlex
import subprocess
import pytest
import time




##################################
# Begin new system setup fixures #
##################################

def _start_process(cmd):
    args = shlex.split(cmd)
    process = subprocess.Popen(args)
    return process

def _start_actorstore():
    os.putenv("FLASK_APP", "/Users/eperspe/Source/calvin-base/calvin/actorstore/store_app.py")
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
