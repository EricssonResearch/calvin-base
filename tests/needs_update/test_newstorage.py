import os
import shlex
import subprocess
import time

import pytest
from mock import Mock
from calvin.runtime.north.storage import Storage
from calvin.runtime.north.plugins.storage.storage_clients import LocalRegistry
from calvin.requests import calvinresponse
# from calvin.runtime.south.async import async
from concurrent.futures import wait


class DummyNode(object):
    """docstring for DummyNode"""
    def __init__(self, arg):
        super(DummyNode, self).__init__()
        self.id = arg
        self.attributes = Mock()
        
        

@pytest.fixture(scope='module', params=('local', 'rest', ))
def registry(request):
    
    def cb(*args, **kwargs):
        print "START OUTER CALLBACK:", args, kwargs
    
    n = DummyNode('testing')
    r = Storage(n, request.param)
    r.start(cb)
    return r


@pytest.fixture()
def localregistry():
    r = LocalRegistry()
    return r

@pytest.fixture()
def mock_callback():
    mock = Mock()
    return mock

#
# Test LocalRegistry API
#
# set(key, value, cb=None):
# get(key, cb):
# delete(key, cb=None):
# FIXME: Add tests for these
# - append(key, value, cb=None):
# - remove(key, value, cb=None):
# FIXME: Later
# - get_iter(key, it, include_key=False):
# - get_concat(key, cb=None):

def test_local_set(localregistry):
    localregistry.set('key', 'value')
    assert localregistry.localstore['key'] == 'value'

def test_local_get_fail(localregistry):
    with pytest.raises(Exception) as e_info:
        ok = localregistry.get('key')
    
def test_local_get(localregistry):
    localregistry.localstore['key'] = 'value'
    assert localregistry.get('key') == 'value'

def test_local_delete(localregistry):
    localregistry.localstore['key'] = 'value'
    localregistry.delete('key')
    assert 'key' not in localregistry.localstore
    

#
# Testing of storage.py API
#

# set(self, prefix, key, value, cb):
# """ Set registry key: prefix+key to be single value: value
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     Callback cb with signature cb(key=key, value=True/False)
#     note that the key here is without the prefix and
#     value indicate success.
# """
# get(self, prefix, key, cb):
# """ Get single value for registry key: prefix+key,
#     first look in locally set but not yet distributed registry
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     Callback cb with signature cb(key=key, value=<retrived value>/CalvinResponse)
#     note that the key here is without the prefix.
#     CalvinResponse object is returned when value is not found.
# """
# delete(self, prefix, key, cb):
# """ Delete registry key: prefix+key
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     This is equivalent to set(..., value=None, ...).
#     Callback cb with signature cb(key=key, value=True/False)
#     note that the key here is without the prefix and
#     value indicate success.
# """

# Required for "flush":
# remove_index
# add_index
# remove
# append


def test_set_get(registry, mock_callback):
    registry.set('prefix', 'key', 'value', None)
    registry.get('prefix', 'key', mock_callback)
    registry.barrier()
    mock_callback.assert_called_with(key='key', value='value')

def test_get_fail(registry, mock_callback):
    registry.delete('prefix', 'key', None)
    registry.barrier()
    registry.get('prefix', 'key', mock_callback)
    registry.barrier()
    # mock_callback.assert_called_with(key='key', value={u'result': u'value'})
    mock_callback.assert_called_once()
    
# def test_get_external(registry, mock_callback):
#     registry.get('', 'external_key', mock_callback)
#     registry.barrier()
#     mock_callback.assert_called_with(key='external_key', value=calvinresponse.CalvinResponse(data='external_value'))
    

def test_delete(registry, mock_callback):
    registry.set('prefix', 'key', 'value', None)
    registry.delete('prefix', 'key', mock_callback)
    registry.barrier()
    # mock_callback.assert_called_with(key='key', value='value')
    mock_callback.assert_called_once()
    
    
# def test_latestart(registry, mock_callback):
#     registry.set('prefix', 'key1', 'value1', None)
#     registry.set('prefix', 'key2', 'value2', None)
#     registry.set('prefix', 'key3', 'value3', None)
#     print registry.localstorage.dump()
#     registry.start()
#     print registry.localstorage.dump()
#     registry.get('prefix', 'key1', mock_callback)
#     mock_callback.assert_called_with(key='key1', value='value1')
    
    
    
        
    

#
# Testing of storage.py remote API
#
# Run a remote client with a LocalRegistry object as dB
#

def _start_process(cmd):
    args = shlex.split(cmd)
    process = subprocess.Popen(args)
    return process

def _start_registry():
    os.putenv("FLASK_APP", "/calvinservices/registry/registry_app.py")
    return _start_process("flask run --port 4998")

def _stop_registry(proc):
    proc.terminate()

# FIXTURE: actorstore
# Setup actorstore for the duration of the test module
@pytest.yield_fixture(scope="module")
def remote_registry():
    # Setup
    reg_proc = _start_registry()
    time.sleep(1)
    # Run tests
    yield
    # Teardown
    _stop_registry(reg_proc)
    
# def test_remote_registry(remote_registry):
#     assert True
    

