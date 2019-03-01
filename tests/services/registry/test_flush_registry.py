
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
from calvin.utilities import calvinresponse


@pytest.fixture()
def _registry(dummy_node):
    r = Storage(dummy_node, 'debug')
    return r

@pytest.fixture()
def _testdata(file_dir):

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
    with open(file_dir+'/tests/services/registry/registry_startup.txt', 'r') as fp:
        _store, _sets = json.load(fp, object_hook=_to_set)
    # Massage keys that are in fact tuples
    _sets = {_expand(k):v for k, v in _sets.items()}

    return (_store, _sets)

def test_sanity(_registry, _testdata):
    def cb(*args, **kwargs):
        # print "START OUTER CALLBACK:", args, kwargs
        pass
    # Keep a reference to the original data
    ref_store, ref_sets = _testdata
    # k, v = ref_sets.popitem()
    # ref_sets = {k:v}
    assert type(_registry.storage) == NullRegistryClient
    assert type(_registry.localstorage) == LocalRegistry
    # Prep the _registry.localstorage (LocalRegistry) with data
    _registry.localstorage.localstore = deepcopy(ref_store)
    _registry.localstorage.localstore_sets = deepcopy(ref_sets)
    # Call start on _registry to trigger change
    # from _registry.localstorage --> _registry.storage
    _registry.start(cb)
    # As a consequence, _registry.storage should now be
    # a DebugRegistryClient, a subclass of LocalRegistry that
    # allow us to easily examine the outcome of the flush operation
    assert type(_registry.storage) == DebugRegistryClient

    # from pprint import pprint
    #
    # print
    # print "_registry.storage.localstore:"
    # pprint(_registry.storage.localstore)
    # print
    # print "ref_store:"
    # pprint(ref_store)
    # print
    # print "_registry.localstorage.localstore:"
    # pprint(_registry.localstorage.localstore)
    #
    #
    # print
    # print "_registry.storage.localstore_sets:"
    # pprint(_registry.storage.localstore_sets)
    # print
    # print "ref_sets:"
    # pprint(ref_sets)
    # print
    # print "_registry.localstorage.localstore_sets:"
    # pprint(_registry.localstorage.localstore_sets)
    #
    # print "\n\nFLUSH!!!\n\n"

    # Trigger flush manually
    _registry.flush_localdata()
    # Now, we can verify that the contents of the _registry.storage
    # is what we expect it to be:
    # print
    # print "_registry.storage.localstore:"
    # pprint(_registry.storage.localstore)
    # print
    # print "ref_store:"
    # pprint(ref_store)
    # print
    # print "_registry.localstorage.localstore:"
    # pprint(_registry.localstorage.localstore)
    assert _registry.storage.localstore == ref_store
    assert _registry.localstorage.localstore == {}
    


    # print
    # print "_registry.storage.localstore_sets:"
    # pprint(_registry.storage.localstore_sets)
    # print
    # print "ref_sets:"
    # pprint(ref_sets)
    # print
    # print "_registry.localstorage.localstore_sets:"
    # pprint(_registry.localstorage.localstore_sets)
    assert _registry.storage.localstore_sets == ref_sets
    assert _registry.localstorage.localstore_sets == {}
    







#
# FIXME: Testing of storage.py remote API
#
# Run a remote client with a LocalRegistry object as dB
#



