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


def _execute_cmd(cmd):
    if isinstance(cmd, basestring):
        cmd = shlex.split(cmd)
    res = subprocess.check_output(cmd)
    return res.strip()


@pytest.fixture(scope='module')
def patch_config(file_dir, working_dir):
    default_config_path = os.path.join(file_dir, "default.conf")
    with open(default_config_path, 'r') as fp:
        config = json.load(fp)

    config["calvinsys"]["capabilities"]["io.stdout"] = {
        "module": "io.filehandler.Descriptor",
        "attributes": {"basedir": "{}".format(working_dir), "filename": "stdout.txt", "mode": "w", "newline": True}
    }
    config["global"]["storage_type"] = "local"

    config_path = os.path.join(working_dir, "calvin.conf")
    with open(config_path, 'w') as fp:
        json.dump(config, fp)
    os.putenv("CALVIN_CONFIG", config_path)

def test_rt(single_runtime_system):
    res = _execute_cmd("cscontrol http://localhost:5001 id")
    res = res.strip('"')
    print res
    assert len(res) == 36
    
def test_store(single_runtime_system):
    res = _execute_cmd("csdocs io")
    assert res.startswith("Module: io")
    
@pytest.mark.parametrize('script', ['capture_output'])
def test_compile_start_stop(single_runtime_system, file_dir, working_dir, script):
    src_path = os.path.join(file_dir, "scripts", script) + ".calvin"
    deployable_path = os.path.join(working_dir, script) + ".json"
    assert '' == _execute_cmd(("cscompile", "--output", deployable_path, src_path))
    status = json.loads(_execute_cmd("cscontrol http://localhost:5001 deploy " + deployable_path))
    app_id = status["application_id"]
    assert len(app_id) == 36
    assert '""' == _execute_cmd("cscontrol http://localhost:5001 applications delete " + app_id)
    file = py.path.local(os.path.join(working_dir, "stdout.txt"))
    assert file.size() > 100

    
    
    
