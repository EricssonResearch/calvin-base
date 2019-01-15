import pytest
import subprocess
import shlex
import os
import time


# Helpers

def _start_process(cmd):
    args = shlex.split(cmd)
    process = subprocess.Popen(args)
    return process

def _start_runtime():
    return _start_process("csruntime -n localhost")
    
def _stop_runtime(proc):
    proc.terminate()
    
    
def _start_actorstore():
    os.putenv("FLASK_APP", "/Users/eperspe/Source/calvin-base/calvin/actorstore/store_app.py")
    return _start_process("flask run --port 4999")

def _stop_actorstore(proc):
    proc.terminate()

def _execute_cmd(cmd):
    args = shlex.split(cmd)
    res = subprocess.check_output(args)
    return res.strip()


@pytest.yield_fixture(scope="module")
def calvin_single_runtime_system():
    # Setup
    rt_proc = _start_runtime()
    as_proc = _start_actorstore()
    # FIXME: Wait for RT to be in listening mode
    time.sleep(1)
        
    # Run tests
    yield
    
    # Teardown
    _stop_actorstore(as_proc)
    _stop_runtime(rt_proc)
    

def test_fixture(calvin_single_runtime_system):
    assert True    
    
def test_rt(calvin_single_runtime_system):
    res = _execute_cmd("cscontrol http://localhost:5001 id")
    res = res.strip('"')
    print res
    assert len(res) == 36
    
def test_store(calvin_single_runtime_system):
    res = _execute_cmd("csdocs io")
    assert res.startswith("Module: io")



