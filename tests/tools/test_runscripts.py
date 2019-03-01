import os
import json

import py
import pytest


system_config = r"""
- class: ACTORSTORE
  name: actorstore
  port: 4999
  type: REST
- class: RUNTIME
  name: runtime
  actorstore: $actorstore
  registry: '{type: local, uri: null}'
"""


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

    config_path = os.path.join(working_dir, "calvin.conf")
    with open(config_path, 'w') as fp:
        json.dump(config, fp)
    os.environ["CALVIN_CONFIG"] = config_path
    yield
    os.environ.pop("CALVIN_CONFIG", None)

def test_rt(system_setup, execute_cmd_check_output):
    res = execute_cmd_check_output("cscontrol {} id".format(system_setup['runtime']['uri']))
    res = res.strip('"')
    assert len(res) == 36
    assert res == system_setup['runtime']['node_id']
    
def test_store(system_setup, execute_cmd_check_output):
    res = execute_cmd_check_output("csdocs io")
    assert res.startswith("Module: io")
    
@pytest.mark.parametrize('script', ['capture_output'])
def test_cscontrol_compile_deploy_delete_cycle(system_setup, execute_cmd_check_output, file_dir, working_dir, script):
    uri = system_setup['runtime']['uri']
    src_path = os.path.join(file_dir, "tests/scripts", script) + ".calvin"
    deployable_path = os.path.join(working_dir, script) + ".json"
    assert '' == execute_cmd_check_output(("cscompile", "--output", deployable_path, src_path))
    out = execute_cmd_check_output("cscontrol {} deploy {}".format(uri, deployable_path))
    print out
    status = json.loads(out)
    app_id = status["application_id"]
    assert len(app_id) == 36
    assert '""' == execute_cmd_check_output("cscontrol {} applications delete {}".format(uri, app_id))
    file = py.path.local(os.path.join(working_dir, "stdout.txt"))
    assert file.size() > 100

    
    
    
