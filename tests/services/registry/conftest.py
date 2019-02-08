import pytest
from mock import MagicMock, Mock

@pytest.fixture()
def org_cb():
    """Mock callback function"""
    m = Mock()
    
    def _once():
        cal = m.call_args_list
        assert len(cal) == 1
        
    def _args():
        cal = m.call_args_list
        args, kwargs = cal[0]
        return (args, kwargs)    
            
    m.assert_once = _once
    m.get_args = _args
    return m
    