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


# FIXTURE: actorstore
# Setup actorstore for the duration of the test module
    

@pytest.fixture()
def _host():
    return "http://localhost:4998"    

@pytest.fixture()
def _registry(_host):
    r = RESTRegistryClient(None, _host)
    return r
    
    
@pytest.fixture(scope='module')
def _session():  
    session = FuturesSession()
    return session

def test_service_sanity(remote_registry, _host):
    response = requests.get(_host+"/dumpstorage")
    assert response.status_code == 200
    # assert response.json() == [{},{}]
    
def test_service_storage(remote_registry, _session, _host):
    response = requests.get(_host+"/storage/foo")
    assert response.status_code == 404
    
    response = requests.post(_host+"/storage/foo", json={'value':'FOO'})
    assert response.status_code == 200
        
    response = requests.get(_host+"/storage/foo")
    assert response.status_code == 200
    assert response.json() == 'FOO'
    
    response = requests.delete(_host+"/storage/foo")
    assert response.status_code == 200
    
    response = requests.get(_host+"/storage/foo")
    assert response.status_code == 404
    
    

def test_set(remote_registry, _registry, _host, org_cb):
    _registry.set('key', 'value', cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
    _registry.barrier()
    org_cb.assert_once()
    # response = requests.get(_host+"/dumpstorage")
    response = requests.get(_host+"/storage/key")
    assert response.status_code == 200
    assert response.json() == 'value'


def test_get(remote_registry, _registry, _host, org_cb):
    _registry.set('key', 'value', cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    _registry.get('key', cb=CalvinCB(func=org_cb, org_key='key', org_cb=None))
    _registry.barrier()
    org_cb.assert_once()
    # response = requests.get(_host+"/dumpstorage")
    response = requests.get(_host+"/storage/key")
    assert response.status_code == 200
    assert response.json() == 'value'
    
def test_delete(remote_registry, _registry, _host, org_cb):
    _registry.set('key', 'value', cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    _registry.barrier()
    _registry.delete('key', cb=CalvinCB(func=org_cb, org_key='key', org_cb=None))
    _registry.barrier()
    org_cb.assert_once()
    # response = requests.get(_host+"/dumpstorage")
    response = requests.get(_host+"/storage/key")
    assert response.status_code == 404

def test_bad_index(remote_registry, _registry, _host, org_cb):
    with pytest.raises(TypeError):    
        _registry.add_index('indexes', 'value')
    with pytest.raises(TypeError):    
        _registry.get_index('indexes', 'value')
    with pytest.raises(TypeError):    
        _registry.remove_index('indexes', 'value')
        
# Since the _registry is the same for the whole module, get and set must be tested in the same function below
# def test_add_index(remote_registry, _registry, _host, org_cb):
#     _registry.add_index(('index1', 'index2'), 'value', cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
#     _registry.add_index(('index1', 'index2'), ('value1', 'value2'), cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
#     _registry.barrier()
#     response = requests.get(_host+"/dumpstorage")
#     org_cb.assert_once()
#     args, kwargs = org_cb.get_args()

def test_get_index(remote_registry, _registry, _host, org_cb):
    _registry.add_index(('index1', 'index2'), ('value1', 'value2'), cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    _registry.barrier()
    _registry.get_index(('index1', 'index2'), cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
    _registry.barrier()
    response = requests.get(_host+"/dumpstorage")
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
    
def test_remove_index(remote_registry, _registry, _host, org_cb):
    _registry.add_index(('index1', 'index2'), ('value1', 'value2'), cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    _registry.barrier()
    _registry.remove_index(('index1', 'index2'), ('value1',), cb=CalvinCB(func=Mock(), org_key='key', org_value='value', org_cb=None))
    _registry.barrier()
    _registry.get_index(('index1', 'index2'), cb=CalvinCB(func=org_cb, org_key='key', org_value='value', org_cb=None))
    _registry.barrier()
    response = requests.get(_host+"/dumpstorage")
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
    # response = requests.get(_host+"/storage_sets/(u'prefix1', u'index1', u'index2')")
    # assert response.status_code == 200
    # print response.json()
    # assert response.json() == {'result': 'value'}
    #
    # assert _registry.localstore_sets[('prefix1', 'index1', 'index2')]['+'] == set(['value'])
    # assert _registry.localstore_sets[('prefix1', 'index1', 'index2')]['-'] == set()
    # assert _registry.localstore_sets[('prefix2', 'index1', 'index2')]['+'] == set(['value1', 'value2'])
    # assert _registry.localstore_sets[('prefix2', 'index1', 'index2')]['-'] == set()
#
# def test_get_index_fail(remote_registry, _registry, _host, org_cb):
#     assert _registry.get_index('prefix1', ('index1', 'index2')) == set()
#
# def test_get_index(remote_registry, _registry, _host, org_cb):
#     _registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     _registry.localstore_sets[('prefix2', 'index1', 'index2')] = {'+': set(['value1', 'value2']), '-': set()}
#     assert _registry.get_index('prefix1', ('index1', 'index2')) == set(['value'])
#     assert _registry.get_index('prefix2', ('index1', 'index2')) == set(('value1', 'value2'))
#
# def test_remove_index(remote_registry, _registry, _host, org_cb):
#     _registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     _registry.localstore_sets[('prefix2', 'index1', 'index2')] = {'+': set(['value1', 'value2']), '-': set()}
#     _registry.remove_index('prefix1', ('index1', 'index2'), 'value')
#     _registry.remove_index('prefix2', ('index1', 'index2'), 'value1')
#     assert _registry.localstore_sets[('prefix1', 'index1', 'index2')] == {'+': set(), '-': set(['value'])}
#     assert _registry.localstore_sets[('prefix2', 'index1', 'index2')] == {'+': set(['value2']), '-': set(['value1'])}
#
# def test_remove_index_nonexisting_value(remote_registry, _registry, _host, org_cb):
#     _registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     _registry.remove_index('prefix1', ('index1', 'index2'), 'value1')
#     assert _registry.localstore_sets[('prefix1', 'index1', 'index2')] == {'+': set(['value']), '-': set(['value1'])}
#
# def test_remove_index_nonexisting_key(remote_registry, _registry, _host, org_cb):
#     _registry.localstore_sets[('prefix1', 'index1', 'index2')] = {'+': set(['value']), '-': set()}
#     _registry.remove_index('prefix2', ('index1', 'index2'), 'value')
#     assert _registry.localstore_sets[('prefix1', 'index1', 'index2')] == {'+': set(['value']), '-': set()}
#     assert _registry.localstore_sets[('prefix2', 'index1', 'index2')] == {'+': set(), '-': set(['value'])}
