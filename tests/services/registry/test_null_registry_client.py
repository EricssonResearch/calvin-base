import pytest
from mock import MagicMock, Mock
from calvin.common.calvin_callback import CalvinCB
from calvin.runtime.north.plugins.storage.storage_clients import NullRegistryClient
import calvin.common.calvinresponse as calvinresponse

@pytest.fixture()
def _registry():
    r = NullRegistryClient()
    return r

@pytest.fixture()
def _mock_cb():
    def getitem(name):
        return None
        
    mock = MagicMock()
    mock.__getitem__.side_effect = getitem
    return mock


# Mandatory for NullRegistryClient
#
# start(self, iface='', name=None, nodeid=None, cb=None):
# set(self, key, value, cb=None):
# get(self, key, cb=None):
# delete(self, key, cb=None):
# add_index(self, prefix, indexes, value, cb=None):
# get_index(self, prefix, indexes, cb=None):
# remove_index(self, prefix, indexes, value, cb=None):
standard_api = [
    ('get', 'key', calvinresponse.NOT_FOUND),
    ('set', 'key', 'value', calvinresponse.OK),
    ('delete', 'key', calvinresponse.OK),
    ('add_index', ('indexes',), 'value', calvinresponse.OK),
    ('remove_index', ('indexes',), 'value', calvinresponse.OK),
]
nonstandard_api = [
    ('start', calvinresponse.OK),
    ('get_index', ('indexes',), None),    
]
api = standard_api + nonstandard_api

# Should not be implemented in NullRegistryClient
# 
# bootstrap(self, addrs, cb=None):
# stop(self, cb=None):
prohibited = [
]

@pytest.mark.parametrize('call', api)
def test_api_present(_registry, _mock_cb, call):
    # _registry.localstore['key'] = 'value'
    name, args = call[0], tuple(call[1:-1])
    method = getattr(_registry, name)
    # Check calling with required numbers of args
    method(*args, cb=_mock_cb)
    # Check calling with named arguments
    kwargs = dict(list(zip([arg[0] if isinstance(arg, (tuple, list, set)) else arg for arg in args], args)))
    method(cb=_mock_cb, **kwargs)

# @pytest.mark.parametrize('call', prohibited)
# def test_api_not_present(_registry, call):
#     name, args = call[0], tuple(call[1:])
#     method = getattr(_registry, name)
#     with pytest.raises(NotImplementedError):
#         method(*args)

#
# Test: methods following the same pattern (return CalvinResponse)
#
@pytest.mark.parametrize('call', standard_api)
def test_forwarding(_registry, org_cb, call):
    name, args, value = call[0], tuple(call[1:-1]), call[-1]
    method = getattr(_registry, name)
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
def test_start(_registry):
    assert False
   
def test_get_index(_registry, org_cb):
    local_values=[1,2,3]
    _registry.get_index(('index1', 'index2'), cb=CalvinCB(func=None, org_key='key', local_values=local_values, org_cb=org_cb))
    org_cb.assert_once()
    _, kwargs = org_cb.get_args()
    # assert kwargs['key'] == 'key'
    assert type(kwargs['value']) is list
    assert kwargs['value'] == local_values
    

    
    
    
    
    
    
