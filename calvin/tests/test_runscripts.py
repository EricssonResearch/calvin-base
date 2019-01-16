import pytest
import subprocess
import shlex
import os
import json
import shutil
import time
import py


# FIXME: Randomize ports
# FIXME: Fixture for test list?

# Helpers

def _start_process(cmd):
    args = shlex.split(cmd)
    process = subprocess.Popen(args)
    return process

def _start_runtime():
    # return _start_process("csruntime -n localhost -l calvinconfig:DEBUG")
    return _start_process("csruntime -n localhost")
    
def _stop_runtime(proc):
    proc.terminate()  
    
def _start_actorstore():
    os.putenv("FLASK_APP", "/Users/eperspe/Source/calvin-base/calvin/actorstore/store_app.py")
    return _start_process("flask run --port 4999")

def _stop_actorstore(proc):
    proc.terminate()

def _execute_cmd(cmd):
    if isinstance(cmd, basestring):
        cmd = shlex.split(cmd)
    res = subprocess.check_output(cmd)
    return res.strip()


@pytest.fixture(scope='module')
def file_dir():
    return os.path.dirname(os.path.realpath(__file__))

def _patch_config(filedir, workdir):
    default_config_path = os.path.join(filedir, "default.conf")
    with open(default_config_path, 'r') as fp:
        config = json.load(fp)
    
    config["calvinsys"]["capabilities"]["io.stdout"] = {
        "module": "io.filehandler.Descriptor",
        "attributes": {"basedir": "{}".format(workdir), "filename": "stdout.txt", "mode": "w", "newline": True}
    }
    config["global"]["storage_type"] = "local"

    config_path = os.path.join(workdir, "calvin.conf")    
    with open(config_path, 'w') as fp:
        json.dump(config, fp)
    os.putenv("CALVIN_CONFIG", config_path)
        
        
@pytest.fixture(scope='module')
def working_dir(tmpdir_factory):
    wdir = tmpdir_factory.mktemp('work')
    wdir = str(wdir)
    return wdir    

@pytest.yield_fixture(autouse=True, scope="module")
def calvin_single_runtime_system(file_dir, working_dir):
    # Setup
    _patch_config(file_dir, working_dir)    
    rt_proc = _start_runtime()
    as_proc = _start_actorstore()
    # FIXME: Wait for RT to be in listening mode
    time.sleep(1)
        
    # Run tests
    yield
    
    # Teardown
    _stop_actorstore(as_proc)
    _stop_runtime(rt_proc)
    
        
def test_rt():
    res = _execute_cmd("cscontrol http://localhost:5001 id")
    res = res.strip('"')
    print res
    assert len(res) == 36
    
def test_store():
    res = _execute_cmd("csdocs io")
    assert res.startswith("Module: io")
    
@pytest.mark.parametrize('script', ['capture_output'])
def test_compile_start_stop(script, file_dir, working_dir):
    src_path = os.path.join(file_dir, "scripts", script) + ".calvin"
    deployable_path = os.path.join(working_dir, script) + ".json"
    assert '' == _execute_cmd(("cscompile", "--output", deployable_path, src_path))
    status = json.loads(_execute_cmd("cscontrol http://localhost:5001 deploy " + deployable_path))
    app_id = status["application_id"]
    assert len(app_id) == 36
    assert '""' == _execute_cmd("cscontrol http://localhost:5001 applications delete " + app_id)
    file = py.path.local(os.path.join(working_dir, "stdout.txt"))
    assert file.size() > 100

    
    
    
