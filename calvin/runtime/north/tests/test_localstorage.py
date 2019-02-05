import pytest
from calvin.runtime.north.plugins.storage.storage_clients import LocalRegistry


@pytest.fixture()
def registry():
    r = LocalRegistry()
    return r

# Mandatory
#
# set(self, key, value, cb=None):
# get(self, key, cb=None):
# delete(self, key, cb=None):
# append(self, key, value, cb=None):
# get_concat(self, key, cb=None):
# remove(self, key, value, cb=None):
# add_index(self, prefix, indexes, value, cb=None):
# get_index(self, prefix, indexes, cb=None):
# remove_index(self, prefix, indexes, value, cb=None):
api = [
    ('get', 'key'), 
    ('set', 'key', 'value'),
    ('delete', 'key'), 
    ('add_index', ('indexes',), 'value'),
    ('get_index', ('indexes',)), 
    ('remove_index', ('indexes',), 'value'), 
]

# Should not be implemented in LocalRegistry
# 
# start(self, iface='', network='', bootstrap=[], cb=None):
# bootstrap(self, addrs, cb=None):
# stop(self, cb=None):
prohibited = [
]

@pytest.mark.parametrize('call', api)
def test_api_present(registry, call):
    registry.localstore['key'] = 'value'
    name, args = call[0], tuple(call[1:])
    method = getattr(registry, name)
    # Check calling with required numbers of args
    method(*args)
    # Check calling with named arguments
    kwargs = dict(zip([arg[0] if isinstance(arg, (tuple, list, set)) else arg for arg in args], args))
    method(**kwargs)

# @pytest.mark.parametrize('call', prohibited)
# def test_api_not_present(registry, call):
#     name, args = call[0], tuple(call[1:])
#     method = getattr(registry, name)
#     with pytest.raises(NotImplementedError):
#         method(*args)

#
# Test: set, get, delete
#
def test_set(registry):
    registry.set('key', 'value')
    assert registry.localstore['key'] == 'value'

def test_get_fail(registry):
    with pytest.raises(KeyError):
        _ = registry.get('key')
    
def test_get(registry):
    registry.localstore['key'] = 'value'
    assert registry.get('key') == 'value'

def test_delete(registry):
    registry.localstore['key'] = 'value'
    assert 'key' in registry.localstore
    registry.delete('key')
    assert 'key' not in registry.localstore
    # Deleting non-present key should not raise exception
    registry.delete('key')
    
#
# Test internal set manipulation: _append, _remove,  
#
def test_append(registry):
    registry._append('key', ('value',))
    assert registry.localstore_sets['key']['+'] == set(['value'])
    assert registry.localstore_sets['key']['-'] == set()
    
def test_append_bad_value(registry):
    with pytest.raises(TypeError):
        registry._append('key', 'value')
        
# def test_get_concat_fail(registry):
#     assert registry.get_concat('key') == []
#
# def test_get_concat(registry):
#     registry.localstore_sets['key'] = {'+': set(['value']), '-': set()}
#     assert registry.get_concat('key') == ['value']

def test_remove(registry):
    registry.localstore_sets['key'] = {'+': set(['value']), '-': set()}
    registry._remove('key', ('value',))
    assert registry.localstore_sets['key']['+'] == set()
    assert registry.localstore_sets['key']['-'] == set(['value'])
#    assert registry.get_concat('key') == []
    # Deleting non-present key should not raise exception    
    registry._remove('key', ('value',))
    
def test_remove_bad_value(registry):
    with pytest.raises(TypeError):    
        registry._remove('key', 'value')
        
    
#
# Test indexed manipulation: add_index, get_index, remove_index
#
def test_add_index_bad_index(registry):
    with pytest.raises(TypeError):    
        registry.add_index('indexes', 'value')

def test_add_index(registry):
    registry.add_index(('index1', 'index2'), 'value')
    registry.add_index(('index1', 'index3'), ('value1', 'value2'))
    assert registry.localstore_sets[('index1', 'index2')]['+'] == set(['value'])
    assert registry.localstore_sets[('index1', 'index2')]['-'] == set()
    assert registry.localstore_sets[('index1', 'index3')]['+'] == set(['value1', 'value2'])
    assert registry.localstore_sets[('index1', 'index3')]['-'] == set()

def test_get_index_fail(registry):
    assert registry.get_index(('index1', 'index2')) == set()

def test_get_index(registry):
    registry.localstore_sets[('index1', 'index2')] = {'+': set(['value']), '-': set()}
    registry.localstore_sets[('index1', 'index3')] = {'+': set(['value1', 'value2']), '-': set()}
    assert registry.get_index(('index1', 'index2')) == set(['value'])
    assert registry.get_index(('index1', 'index3')) == set(('value1', 'value2'))
    assert registry.get_index(('index1',)) == set(('value', 'value1', 'value2'))
    

def test_remove_index(registry):
    registry.localstore_sets[('index1', 'index2')] = {'+': set(['value']), '-': set()}
    registry.localstore_sets[('index1', 'index3')] = {'+': set(['value1', 'value2']), '-': set()}
    registry.remove_index(('index1', 'index2'), 'value')
    registry.remove_index(('index1', 'index3'), 'value1')
    assert registry.localstore_sets[('index1', 'index2')] == {'+': set(), '-': set(['value'])}
    assert registry.localstore_sets[('index1', 'index3')] == {'+': set(['value2']), '-': set(['value1'])}
    
def test_remove_index_nonexisting_value(registry):
    registry.localstore_sets[('index1', 'index2')] = {'+': set(['value']), '-': set()}
    registry.remove_index(('index1', 'index2'), 'value1')
    assert registry.localstore_sets[('index1', 'index2')] == {'+': set(['value']), '-': set(['value1'])}
    
def test_remove_index_nonexisting_key(registry):
    registry.localstore_sets[('index1', 'index2')] = {'+': set(['value']), '-': set()}
    registry.remove_index(('index1', 'index3'), 'value')
    assert registry.localstore_sets[('index1', 'index2')] == {'+': set(['value']), '-': set()}
    assert registry.localstore_sets[('index1', 'index3')] == {'+': set(), '-': set(['value'])}

    
    
    
    
    
    
