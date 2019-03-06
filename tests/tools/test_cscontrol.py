import os
import subprocess
import json

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


testlist = [
    ("")
]

def test_bad_command(system_setup, execute_cmd_check_output):
    with pytest.raises(subprocess.CalledProcessError):
        res = execute_cmd_check_output(("cscontrol"))

def test_id(system_setup, execute_cmd_check_output):
    uri = system_setup['runtime']['uri']
    res = execute_cmd_check_output(("cscontrol", uri, "id"))
    res = res.strip('"')
    assert res == system_setup['runtime']['node_id']
    
def test_deploy(system_setup, execute_cmd_check_output, file_dir):
    uri = system_setup['runtime']['uri']
    deployable_path = os.path.join(file_dir, "tests/scripts/test1.json")
    res = execute_cmd_check_output(("cscontrol", uri, "deploy", deployable_path))
    deploy_info = json.loads(res)
    assert 'application_id' in res
    