
import os
import shlex
import subprocess
import time
import json
from copy import deepcopy
import pytest
from mock import Mock
from calvin.runtime.north.storage import Storage
from calvin.runtime.north.plugins.storage.storage_clients import LocalRegistry, NullRegistryClient, DebugRegistryClient
from calvin.requests import calvinresponse


class DummyNode(object):
    """docstring for DummyNode"""
    def __init__(self, arg):
        super(DummyNode, self).__init__()
        self.id = arg
        self.attributes = Mock()


@pytest.fixture()
def registry():
    n = DummyNode('testing')
    r = Storage(n, 'debug')
    return r


# @pytest.fixture()
# def localregistry():
#     r = LocalRegistry()
#     return r

@pytest.fixture()
def mock_callback():
    mock = Mock()
    return mock

@pytest.fixture()
def testdata():

    def _to_set(o):
        """Convert JSON testdata special dicts to sets"""
        if "__SET__" in o:
            return set(o["__SET__"])
        return o

    def _expand(k):
        """Convert JSON testdata encoded tuples to tuples"""
        if not k.startswith('#'):
            return k
        items = k[1:].split(',')
        return tuple(items)

    # Read testdata from file
    with open('calvin/runtime/north/tests/registry_startup.txt', 'r') as fp:
        _store, _sets = json.load(fp, object_hook=_to_set)
    # Massage keys that are in fact tuples
    _sets = {_expand(k):v for k, v in _sets.items()}

    return (_store, _sets)

def test_sanity(registry, testdata):
    def cb(*args, **kwargs):
        # print "START OUTER CALLBACK:", args, kwargs
        pass
    # Keep a reference to the original data
    ref_store, ref_sets = testdata
    # k, v = ref_sets.popitem()
    # ref_sets = {k:v}
    assert type(registry.storage) == NullRegistryClient
    assert type(registry.localstorage) == LocalRegistry
    # Prep the registry.localstorage (LocalRegistry) with data
    registry.localstorage.localstore = deepcopy(ref_store)
    registry.localstorage.localstore_sets = deepcopy(ref_sets)
    # Call start on registry to trigger change
    # from registry.localstorage --> registry.storage
    registry.start(None, cb)
    # As a consequence, registry.storage should now be
    # a DebugRegistryClient, a subclass of LocalRegistry that
    # allow us to easily examine the outcome of the flush operation
    assert type(registry.storage) == DebugRegistryClient

    # from pprint import pprint
    #
    # print
    # print "registry.storage.localstore:"
    # pprint(registry.storage.localstore)
    # print
    # print "ref_store:"
    # pprint(ref_store)
    # print
    # print "registry.localstorage.localstore:"
    # pprint(registry.localstorage.localstore)
    #
    #
    # print
    # print "registry.storage.localstore_sets:"
    # pprint(registry.storage.localstore_sets)
    # print
    # print "ref_sets:"
    # pprint(ref_sets)
    # print
    # print "registry.localstorage.localstore_sets:"
    # pprint(registry.localstorage.localstore_sets)
    #
    # print "\n\nFLUSH!!!\n\n"

    # Trigger flush manually
    registry.flush_localdata()
    # Now, we can verify that the contents of the registry.storage
    # is what we expect it to be:
    # print
    # print "registry.storage.localstore:"
    # pprint(registry.storage.localstore)
    # print
    # print "ref_store:"
    # pprint(ref_store)
    # print
    # print "registry.localstorage.localstore:"
    # pprint(registry.localstorage.localstore)
    assert registry.storage.localstore == ref_store
    assert registry.localstorage.localstore == {}
    


    # print
    # print "registry.storage.localstore_sets:"
    # pprint(registry.storage.localstore_sets)
    # print
    # print "ref_sets:"
    # pprint(ref_sets)
    # print
    # print "registry.localstorage.localstore_sets:"
    # pprint(registry.localstorage.localstore_sets)
    assert registry.storage.localstore_sets == ref_sets
    assert registry.localstorage.localstore_sets == {}
    







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

# def test_remote_registry(remote_registry):
#     assert True


