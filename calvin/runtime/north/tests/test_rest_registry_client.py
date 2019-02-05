import os
import shlex
import subprocess
import time

import pytest
from mock import MagicMock, Mock
from calvin.utilities.calvin_callback import CalvinCB
from calvin.runtime.north.plugins.storage.storage_clients import RESTRegistryClient
import calvin.requests.calvinresponse as calvinresponse
import requests
from requests_futures.sessions import FuturesSession
# from requests_futures.sessions import FuturesSession
# import concurrent.futures

#
# Testing of remote storage
#

def _start_process(cmd):
    args = shlex.split(cmd)
    process = subprocess.Popen(args)
    return process

def _start_registry():
    os.putenv("FLASK_APP", "calvinservices/registry/registry_app.py")
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
    

@pytest.fixture()
def host():
    return "http://localhost:4998"    

@pytest.fixture()
def registry(host):
    r = RESTRegistryClient(None, host)
    return r
    
    
@pytest.fixture(scope='module')
def session():  
    session = FuturesSession()
    return session

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

def test_service_sanity(remote_registry, host):
    response = requests.get(host+"/dumpstorage")
    assert response.status_code == 200
    # assert response.json() == [{},{}]
    
def test_service_storage(remote_registry, session, host):
    response = requests.get(host+"/storage/foo")
    assert response.status_code == 404
    
    response = requests.post(host+"/storage/foo", json={'value':'FOO'})
    assert response.status_code == 200
        
    response = requests.get(host+"/storage/foo")
    assert response.status_code == 200
    assert response.json() == 'FOO'
    
    response = requests.delete(host+"/storage/foo")
    assert response.status_code == 200
    
    response = requests.get(host+"/storage/foo")
    assert response.status_code == 404
    
    

def test_set(remote_registry, registry, host, org_cb):
    registry.set('key', 'value', cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
    registry.barrier()
    org_cb.assert_once()
    # response = requests.get(host+"/dumpstorage")
    response = requests.get(host+"/storage/key")
    assert response.status_code == 200
    assert response.json() == 'value'


def test_get(remote_registry, registry, host, org_cb):
    registry.set('key', 'value', cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    registry.get('key', cb=CalvinCB(func=org_cb, org_key='key', org_cb=None))
    registry.barrier()
    org_cb.assert_once()
    # response = requests.get(host+"/dumpstorage")
    response = requests.get(host+"/storage/key")
    assert response.status_code == 200
    assert response.json() == 'value'
    
def test_delete(remote_registry, registry, host, org_cb):
    registry.set('key', 'value', cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    registry.barrier()
    registry.delete('key', cb=CalvinCB(func=org_cb, org_key='key', org_cb=None))
    registry.barrier()
    org_cb.assert_once()
    # response = requests.get(host+"/dumpstorage")
    response = requests.get(host+"/storage/key")
    assert response.status_code == 404

def test_bad_index(remote_registry, registry, host, org_cb):
    with pytest.raises(TypeError):    
        registry.add_index('indexes', 'value')
    with pytest.raises(TypeError):    
        registry.get_index('indexes', 'value')
    with pytest.raises(TypeError):    
        registry.remove_index('indexes', 'value')
        
# Since the registry is the same for the whole module, get and set must be tested in the same function below
# def test_add_index(remote_registry, registry, host, org_cb):
#     registry.add_index(('index1', 'index2'), 'value', cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
#     registry.add_index(('index1', 'index2'), ('value1', 'value2'), cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
#     registry.barrier()
#     response = requests.get(host+"/dumpstorage")
#     org_cb.assert_once()
#     args, kwargs = org_cb.get_args()

def test_get_index(remote_registry, registry, host, org_cb):
    registry.add_index(('index1', 'index2'), ('value1', 'value2'), cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    registry.barrier()
    registry.get_index(('index1', 'index2'), cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
    registry.barrier()
    response = requests.get(host+"/dumpstorage")
    org_cb.assert_once()
    args, kwargs = org_cb.get_args()
    print args, kwargs
    assert 'value' in kwargs
    # assert 'result' in kwargs['value']
    # assert kwargs['value']['result'] == ['value1', 'value2']
    result = kwargs['value']
    assert 'value1' in result and 'value2' in result
    assert len(result) == 2
    assert set(('value1', 'value2')) == set(result)
    
def test_remove_index(remote_registry, registry, host, org_cb):
    registry.add_index(('index1', 'index2'), ('value1', 'value2'), cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    registry.barrier()
    registry.remove_index(('index1', 'index2'), ('value1',), cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    registry.barrier()
    registry.get_index(('index1', 'index2'), cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
    registry.barrier()
    response = requests.get(host+"/dumpstorage")
    org_cb.assert_once()
    args, kwargs = org_cb.get_args()
    assert 'value' in kwargs
    # assert 'result' in kwargs['value']
    result = kwargs['value']
    assert 'value2' in result
    assert len(result) == 1
    assert set(('value2',)) == set(result)
    
    
# FIXME: Add tests for failed request    
    
    #
    # print response.json()
    # response = requests.get(host+"/storage_sets/(u'prefix1', u'index1', u'index2')")
    # assert response.status_code == 200
    # print response.json()
    # assert response.json() == {'result': 'value'}
    #
    # assert registry.localstore_sets[('prefix1', 'index1', 'index2')]['+'] == set(['value'])
    # assert registry.localstore_sets[('prefix1', 'index1', 'index2')]['-'] == set()
    # assert registry.localstore_sets[('prefix2', 'index1', 'index2')]['+'] == set(['value1', 'value2'])
    # assert registry.localstore_sets[('prefix2', 'index1', 'index2')]['-'] == set()
#
# def test_get_index_fail(remote_registry, registry, host, org_cb):
#     assert registry.get_index('prefix1', ('index1', 'index2')) == set()
#
# def test_get_index(remote_registry, registry, host, org_cb):
#     registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     registry.localstore_sets[('prefix2', 'index1', 'index2')] = {'+': set(['value1', 'value2']), '-': set()}
#     assert registry.get_index('prefix1', ('index1', 'index2')) == set(['value'])
#     assert registry.get_index('prefix2', ('index1', 'index2')) == set(('value1', 'value2'))
#
# def test_remove_index(remote_registry, registry, host, org_cb):
#     registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     registry.localstore_sets[('prefix2', 'index1', 'index2')] = {'+': set(['value1', 'value2']), '-': set()}
#     registry.remove_index('prefix1', ('index1', 'index2'), 'value')
#     registry.remove_index('prefix2', ('index1', 'index2'), 'value1')
#     assert registry.localstore_sets[('prefix1', 'index1', 'index2')] == {'+': set(), '-': set(['value'])}
#     assert registry.localstore_sets[('prefix2', 'index1', 'index2')] == {'+': set(['value2']), '-': set(['value1'])}
#
# def test_remove_index_nonexisting_value(remote_registry, registry, host, org_cb):
#     registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     registry.remove_index('prefix1', ('index1', 'index2'), 'value1')
#     assert registry.localstore_sets[('prefix1', 'index1', 'index2')] == {'+': set(['value']), '-': set(['value1'])}
#
# def test_remove_index_nonexisting_key(remote_registry, registry, host, org_cb):
#     registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     registry.remove_index('prefix2', ('index1', 'index2'), 'value')
#     assert registry.localstore_sets[('prefix1', 'index1', 'index2')] == {'+': set(['value']), '-': set()}
#     assert registry.localstore_sets[('prefix2', 'index1', 'index2')] == {'+': set(), '-': set(['value'])}
