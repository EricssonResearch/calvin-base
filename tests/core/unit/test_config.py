import os
import json

import pytest
import yaml

from calvin.common import calvinconfig
from tests import orchestration

def test_default_config(working_dir):
    # Verify that the default config file used in the tests is identical to 
    # the builtin default config 
    default_config_file = os.path.join(working_dir, "default.conf")
    assert os.path.isfile(default_config_file)
    with open(default_config_file, 'r') as fp:
        default_test_conf = json.load(fp)
    # print(json.dumps(default_test_conf, indent=4, sort_keys=True))
    conf = calvinconfig.CalvinConfig()
    # builtin_config_file = os.path.join(working_dir, "builtin.conf")
    # conf.write_default_config(builtin_config_file)
    builtin_conf = conf.default_config()
    # print("-"*79)
    # print(json.dumps(builtin_conf, indent=4, sort_keys=True))
    assert builtin_conf == default_test_conf
    

testlist = [
    (
        'dumb_patch_global', 
        """
        - class: RUNTIME
          name: runtime
          config:
            global: {}
        """,
        {},
    ),
    (
        'patch_global',
        """
        - class: RUNTIME
          name: runtime
          config:
            global:
              storage_type: rest
              storage_host: http://some.host:9999
        """,
        {
            "global:storage_type": "rest",
            "global:storage_host": "http://some.host:9999"
        }
    ),
    (
        'patch_calvinsys',
        """
        - class: RUNTIME
          name: runtime
          config:
            calvinsys:
              capabilities:
                io.stdout:
                  module: io.filehandler.Descriptor
                  attributes:
                    basedir: foo
                    filename: stdout.txt
                    mode: w
                    newline: true
        """, 
        {
            "calvinsys:io.stdout": {
                "module": "io.filehandler.Descriptor",
                "attributes": {
                    "basedir": "foo",
                    "filename": "stdout.txt",
                    "mode": "w", 
                    "newline": True
                }
            }
        }
    )
]


@pytest.mark.parametrize('test', testlist, ids=lambda x: x[0])    
def test_patching(working_dir, test):
    name, sys_yaml, expected = test
    
    sys_def = yaml.load(sys_yaml)
    sm = orchestration.SystemManager(sys_def, working_dir, start=False)
    rt_name = list(sm.info.keys())[0]
    rt_config_file = os.path.join(working_dir, "{}.conf".format(rt_name))
    assert os.path.isfile(rt_config_file)
    with open(rt_config_file, 'r') as fp:
        conf = json.load(fp)
    # print(conf)
    cc = calvinconfig.CalvinConfig()
    default_conf = cc.default_config()
    
    for section, content in conf.items():
        for key, value in content.items():
            keypath = "{}:{}".format(section, key)
            if keypath in expected:
                assert value == expected[keypath]
            else:
                # config value should be present and unchanged
                assert value == default_conf[section][key]
                
                
         
        
    
        
    

    
    
    
    