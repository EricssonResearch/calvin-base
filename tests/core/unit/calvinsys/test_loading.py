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
    
def test_singleton():
    cs = calvinsys.get_calvinsys()
    assert cs
    assert cs.capabilities == {}
    cs.init(Mock())
    assert cs.capabilities
    cs1 = calvinsys.get_calvinsys()
    # Verify that we got the initiated singleton instance:
    assert cs1 == cs
    assert cs1.capabilities
    # Verify that this creates a new instance
    cs2 = calvinsys.CalvinSys()
    assert cs2 != cs
    assert cs2.capabilities == {}
    
def test_multiple_init():
    cs = calvinsys.CalvinSys()
    assert cs
    assert cs.capabilities == {}
    cs.init(Mock())
    assert cs.capabilities
    cs.init(Mock())
    assert cs.capabilities
    

def test_loading():
    cs = calvinsys.CalvinSys()
    assert cs
    cs.init(Mock())
    assert cs.capabilities
    for cap in cs.capabilities:
        capability, pyclass = cs._get_class(cap)
        assert capability
        assert pyclass
    