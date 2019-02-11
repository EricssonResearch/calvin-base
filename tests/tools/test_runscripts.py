import os
import json

import py
import pytest


# FIXME: Randomize ports
# FIXME: Fixture for test list?

@pytest.fixture(scope='module')
def patch_config(file_dir, working_dir):
    """Patch copy of default.conf in temp dir; set env CALVIN_CONFIG to patched file"""
    default_config_path = os.path.join(file_dir, "tests/default.conf")
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

def test_rt(single_runtime_system, execute_cmd_check_output):
    res = execute_cmd_check_output("cscontrol {} id".format(single_runtime_system))
    res = res.strip('"')
    assert len(res) == 36
    
def test_store(single_runtime_system, execute_cmd_check_output):
    res = execute_cmd_check_output("csdocs io")
    assert res.startswith("Module: io")
    
@pytest.mark.parametrize('script', ['capture_output'])
def test_cscontrol_compile_deploy_delete_cycle(single_runtime_system, execute_cmd_check_output, file_dir, working_dir, script):
    src_path = os.path.join(file_dir, "tests/needs_update/scripts", script) + ".calvin"
    deployable_path = os.path.join(working_dir, script) + ".json"
    assert '' == execute_cmd_check_output(("cscompile", "--output", deployable_path, src_path))
    status = json.loads(execute_cmd_check_output("cscontrol {} deploy {}".format(single_runtime_system, deployable_path)))
    app_id = status["application_id"]
    assert len(app_id) == 36
    assert '""' == execute_cmd_check_output("cscontrol {} applications delete {}".format(single_runtime_system, app_id))
    file = py.path.local(os.path.join(working_dir, "stdout.txt"))
    assert file.size() > 100

    
    
    
