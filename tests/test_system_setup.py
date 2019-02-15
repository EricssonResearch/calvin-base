import os

import pytest

system_config_file = "SystemYAML.yaml"

# system_config = r"""
# - class: REGISTRY
#   name: registry
#   port: 4998
#   type: REST
# """

def test_it(system_setup):
    print system_setup
        
def test_another(system_setup):
    print len(system_setup)
    
    