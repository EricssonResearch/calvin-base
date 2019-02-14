import os

import pytest
import yaml

import orchestration

system_config_list = [
    "SystemYAML.yaml",
    "SystemJSON.json"
]


@pytest.fixture(params=system_config_list)
def system_setup(request, file_dir):
    config_file = os.path.join(file_dir, 'tests/systems', request.param)
    with open(config_file, 'r') as fp:
        system_config = yaml.load(fp)
    sysmgr = orchestration.SystemManager(system_config)
    yield sysmgr.info
    sysmgr.teardown()
    
def test_it(system_setup):
    print
    for s in system_setup:
        print s, system_setup[s] 
        
    