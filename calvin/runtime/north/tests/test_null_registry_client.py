import pytest
from mock import MagicMock, Mock
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.north.storage_clients import NullRegistryClient
import calvin.requests.calvinresponse as calvinresponse

@pytest.fixture()
def registry():
    r = NullRegistryClient(storage_type = 'local')
    return r

@pytest.fixture()
def mock_cb():
    def getitem(name):
        return None
        
    mock = MagicMock()
    mock.__getitem__.side_effect = getitem
    return mock

@pytest.fixture()
def org_cb():
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


# Mandatory for NullRegistryClient
#
# start(self, iface='', name=None, nodeid=None, cb=None):
# set(self, key, value, cb=None):
# get(self, key, cb=None):
# delete(self, key, cb=None):
# append(self, key, value, cb=None):
# get_concat(self, key, cb=None):
# remove(self, key, value, cb=None):
# add_index(self, prefix, indexes, value, cb=None):
# get_index(self, prefix, indexes, cb=None):
# remove_index(self, prefix, indexes, value, cb=None):
standard_api = [
    ('get', 'key', calvinresponse.NOT_FOUND),
    ('set', 'key', 'value', calvinresponse.OK),
    ('delete', 'key', calvinresponse.OK),
    ('append', 'key', ('value',), calvinresponse.OK),
    ('remove', 'key', ('value',), calvinresponse.OK),
    ('add_index', 'prefix', ('indexes',), 'value', calvinresponse.OK),
    ('remove_index', 'prefix', ('indexes',), 'value', calvinresponse.OK),
]
nonstandard_api = [
    ('start', 'iface', 'name', 'nodeid', None),
    ('get_concat', 'key', None),
    ('get_index', 'prefix', ('indexes',), None),    
]
api = standard_api + nonstandard_api

# Should not be implemented in NullRegistryClient
# 
# bootstrap(self, addrs, cb=None):
# stop(self, cb=None):
prohibited = [
    ('stop', ''),
    ('bootstrap', ''),
]

@pytest.mark.parametrize('call', api)
def test_api_present(registry, mock_cb, call):
    # registry.localstore['key'] = 'value'
    name, args = call[0], tuple(call[1:-1])
    method = getattr(registry, name)
    # Check calling with required numbers of args
    method(*args, cb=mock_cb)
    # Check calling with named arguments
    kwargs = dict(zip([arg[0] if isinstance(arg, (tuple, list, set)) else arg for arg in args], args))
    method(cb=mock_cb, **kwargs)

@pytest.mark.parametrize('call', prohibited)
def test_api_not_present(registry, call):
    name, args = call[0], tuple(call[1:])
    method = getattr(registry, name)
    with pytest.raises(NotImplementedError):
        method(*args)

#
# Test: methods following the same pattern (return CalvinResponse)
#
@pytest.mark.parametrize('call', standard_api)
def test_forwarding(registry, org_cb, call):
    name, args, value = call[0], tuple(call[1:-1]), call[-1]
    method = getattr(registry, name)
    method(*args, cb=CalvinCB(func=None, org_key='key', org_value='value', org_cb=org_cb))
    org_cb.assert_once()
    _, kwargs = org_cb.get_args()
    assert kwargs['key'] == 'key'
    assert type(kwargs['value']) is calvinresponse.CalvinResponse
    assert kwargs['value'] == value

#
# Test: methods not following the same pattern as above
#
@pytest.mark.skip(reason="Add test when first remote client has been added")
def test_start(registry):
    assert False

def test_get_concat(registry, org_cb):
    local_list=[1,2,3]
    registry.get_concat('key', cb=CalvinCB(func=None, org_key='key', local_list=local_list, org_cb=org_cb))
    org_cb.assert_once()
    _, kwargs = org_cb.get_args()
    assert kwargs['key'] == 'key'
    assert type(kwargs['value']) is list
    assert kwargs['value'] == local_list
   
def test_get_index(registry, org_cb):
    local_values=[1,2,3]
    registry.get_index('prefix1', ('index1', 'index2'), cb=CalvinCB(func=None, org_key='key', local_values=local_values, org_cb=org_cb))
    org_cb.assert_once()
    _, kwargs = org_cb.get_args()
    # assert kwargs['key'] == 'key'
    assert type(kwargs['value']) is list
    assert kwargs['value'] == local_values
    

    
    
    
    
    
    
