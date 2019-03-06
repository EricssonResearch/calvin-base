import pytest
from mock import Mock

import calvin.runtime.north.calvinsys as calvinsys

# FIXME: [ ] Runnig CalvinSys.init() twice (even in subsequent tests) 
#            does not work since it overwrites the original data
#        [ ] Config must be isolated so it won't pick up stray config files  

def test_sanity():
    cs = calvinsys.CalvinSys()
    assert cs
    assert cs.capabilities == {}
    
# def test_init(default_config):
#     cs = calvinsys.CalvinSys()
#     assert cs
#     cs.init(Mock())
#     assert cs.capabilities
#     #print(cs.capabilities)
    
def test_loading():
    cs = calvinsys.CalvinSys()
    assert cs
    cs.init(Mock())
    assert cs.capabilities
    for cap in cs.capabilities:
        capability, pyclass = cs._get_class(cap)
    