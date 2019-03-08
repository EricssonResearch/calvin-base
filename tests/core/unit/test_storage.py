from unittest.mock import Mock
import pytest
import yaml

from calvin.runtime.north.storage import Storage
from calvin.runtime.north.calvincontrol import get_calvincontrol
from calvin.runtime.north.calvin_network import CalvinNetwork
from calvin.runtime.north.calvin_proto import CalvinProto
from calvin.common.calvin_callback import CalvinCB
from calvin.common import dynops
import tests.orchestration as orchestration


storage_configs = [
    (
        'local', None, "[]"),
    (
        'rest', 
        "http://127.0.0.1:4998", 
        """
        - class: REGISTRY
          name: registry
          port: 4998
          type: REST
        """
    ),    
    (
        'proxy', 
        "http://127.0.0.1:5000", 
        """
        - class: RUNTIME
          name: runtime1
          port: 5001
          rt2rt_port: 5000
          registry: {'type':'local', 'uri':null}
        """
    ),
    (
        'proxy', 
        "http://127.0.0.1:5000", 
        """
        - class: REGISTRY
          name: registry
          port: 4998
          type: REST
        - class: RUNTIME
          name: runtime1
          port: 5001
          rt2rt_port: 5000
          registry: $registry
        """
    ),
]

storage_configs = storage_configs

@pytest.fixture(scope='module', params=storage_configs)
def _storage(request):
    """
    Setup a test system according to a system config in YAML or JSON and pass 
    the system info to the tests.
    
    The test module must define either 
    - 'system_config_file' to name a config file in 'tests/systems/', or
    - 'system_config' to be a string with the system config
    where the latter is suitable for very simple setups only.
    
    This fixture relies on the tool-suite (csruntime et al.) so it is probably 
    a good idea to make sure that they are tested first.

    This fixture pretty much replaces all previous fixtures and avoids 
    monkeypatching environment etc.    
    """
    mode, host, system_config = request.param
    config = yaml.load(system_config)
    sysmgr = orchestration.SystemManager(config)
    # Give the dummy node communication power (for proxy tests)
    node = Mock()
    node.control = get_calvincontrol()
    node.network = CalvinNetwork(node)
    node.proto = CalvinProto(node, node.network)
    storage = Storage(node, mode, host)
    storage.start()    

    yield storage

    sysmgr.teardown()
    
    
# def test_foo(system_setup2):
#     assert system_setup2 in [1, 2]
        

    
# set(self, prefix, key, value, cb):
# """ Set registry key: prefix+key to be single value: value
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     Callback cb with signature cb(key=key, value=True/False)
#     note that the key here is without the prefix and
#     value indicate success.
# """
# 
# get(self, prefix, key, cb):
# """ Get single value for registry key: prefix+key,
#     first look in locally set but not yet distributed registry
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     Callback cb with signature cb(key=key, value=<retrived value>/CalvinResponse)
#     note that the key here is without the prefix.
#     CalvinResponse object is returned when value is not found.
# """
# 
# 
# get_iter(self, prefix, key, it, include_key=False):
# """ Get single value for registry key: prefix+key,
#     first look in locally set but not yet distributed registry.
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     Value is placed in supplied dynamic iterable it parameter.
#     The dynamic iterable are of a subclass to calvin.common.dynops.DynOps
#     that supports the append function call (currently only List), see DynOps
#     for details of how they are used. It is common to call auto_final method
#     with parameter max_length to number of get_iter calls.
#     If a key is not found the special value dynops.FailedElement is put in the
#     iterable. When the parameter include_key is True a tuple of (key, value)
#     is placed in it instead of only the retrived value,
#     note that the key here is without the prefix.
#     Value is False when value has been deleted and
#     None if never set (this is current behaviour and might change).
# """
# 
# delete(self, prefix, key, cb):
# """ Delete registry key: prefix+key
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     This is equivalent to set(..., value=None, ...).
#     Callback cb with signature cb(key=key, value=True/False)
#     note that the key here is without the prefix and
#     value indicate success.
# """

def test_set_get_delete(_storage):
    def cb(expected, *args, **kwargs):
        assert not args
        assert len(kwargs) == 2
        assert 'key' in kwargs 
        assert 'value' in kwargs
        if expected:
            assert kwargs['value'] == expected
        
    _storage.set('prefix', 'key', 'value', cb=CalvinCB(cb, expected=200))
    _storage.get('prefix', 'key', cb=CalvinCB(cb, expected='value'))
    _storage.delete('prefix', 'key', cb=CalvinCB(cb, expected=200))
    _storage.get('prefix', 'key', cb=CalvinCB(cb, expected=404))
    

# get_iter(self, prefix, key, it, include_key=False):
# """ Get single value for registry key: prefix+key,
#     first look in locally set but not yet distributed registry.
#     It is assumed that the prefix and key are strings,
#     the sum has to be an immutable object.
#     Value is placed in supplied dynamic iterable it parameter.
#     The dynamic iterable are of a subclass to calvin.common.dynops.DynOps
#     that supports the append function call (currently only List), see DynOps
#     for details of how they are used. It is common to call auto_final method
#     with parameter max_length to number of get_iter calls.
#     If a key is not found the special value dynops.FailedElement is put in the
#     iterable. When the parameter include_key is True a tuple of (key, value)
#     is placed in it instead of only the retrived value,
#     note that the key here is without the prefix.
#     Value is False when value has been deleted and
#     None if never set (this is current behaviour and might change).
# """

@pytest.mark.skip(reason="Can't test this without async support")
def test_get_iter(_storage):
    it = dynops.List()
    _storage.set('prefix', 'key', 'value', cb=None)
    _storage.get_iter('prefix', 'key', it)
    value = next(it)
    assert value == 'value'
    with pytest.raises(Exception) as exc_info:
        value = next(it)
    assert exc_info.type is dynops.PauseIteration
    it = dynops.List()
    _storage.get_iter('prefix', 'key', it, include_key=True)
    value = next(it)
    assert value == ('prefixkey', 'value')
    with pytest.raises(Exception) as exc_info:
        value = next(it)
    assert exc_info.type is dynops.PauseIteration
    
    
# add_index(self, index, value, root_prefix_level=None, cb=None):
# """
# Add single value (e.g. a node id) or list to a set stored in registry
# later retrivable for each level of the index.
# index: The multilevel key:
#        a string with slash as delimiter for finer level of index,
#        e.g. node/address/example_street/3/buildingA/level3/room3003,
#        index string must been escaped with \/ and \\ for / and \ within levels
#        OR a list of each levels strings
# value: the value or list that is to be added to the set stored at each level of the index
# root_prefix_level: the top level of the index that can be searched separately,
#        with e.g. =1 then node/address can't be split
# cb: Callback with signature cb(value=<CalvinResponse>)
#     value indicate success.
# """

# remove_index(self, index, value, root_prefix_level=None, cb=None):
# """
# Remove single value (e.g. a node id) or list from a set stored in registry
# index: The multilevel key:
#        a string with slash as delimiter for finer level of index,
#        e.g. node/address/example_street/3/buildingA/level3/room3003,
#        node/affiliation/owner/com.ericsson/Harald,
#        node/affiliation/name/com.ericsson/laptop,
#        index string must been escaped with \/ and \\ for / and \ within levels
#        OR a list of each levels strings
# value: the value or list that is to be removed from the set stored at each level of the index
# root_prefix_level: the top level of the index that can be searched separately,
#        with e.g. =1 then node/address can't be split
# cb: Callback with signature cb(value=<CalvinResponse>)
#     note that the key here is without the prefix and
#     value indicate success.
# """
#
# delete_index(self, index, root_prefix_level=None, cb=None):
# """
# Delete index entry in registry - this have the semantics of
# remove_index(index, get_index(index)) - NOT IMPLEMENTED since never used
# index: The multilevel key:
#        a string with slash as delimiter for finer level of index,
#        e.g. node/address/example_street/3/buildingA/level3/room3003,
#        node/affiliation/owner/com.ericsson/Harald,
#        node/affiliation/name/com.ericsson/laptop,
#        index string must been escaped with \/ and \\ for / and \ within levels
#        OR a list of each levels strings
# root_prefix_level: the top level of the index that can be searched separately,
#        with e.g. =1 then node/address can't be split
# cb: Callback with signature cb(value=<CalvinResponse>)
#     value indicate success.
# """
#
# raise NotImplementedError()
#
# get_index(self, index, root_prefix_level=None, cb=None):
# """
# Get multiple values from the registry stored at the index level or
# below it in hierarchy.
# index: The multilevel key:
#        a string with slash as delimiter for finer level of index,
#        e.g. node/address/example_street/3/buildingA/level3/room3003,
#        node/affiliation/owner/com.ericsson/Harald,
#        node/affiliation/name/com.ericsson/laptop,
#        index string must been escaped with \/ and \\ for / and \ within levels
#        OR a list of each levels strings
# cb: Callback cb with signature cb(value=<retrived values>),
#     value is a list.
#
# The registry can be eventually consistent,
# e.g. a removal of a value might only have reached part of a
# distributed registry and hence still be part of returned
# list of values, it may also miss values added by others but
# not yet distributed.
# """
#

def test_add_remove_get_delete_index(_storage):
    def cb(expected, *args, **kwargs):
        assert not args
        if 'key' in kwargs:
            # FIXME: Why is this?
            assert kwargs['key'] == 'NO-SUCH-KEY'
        assert 'value' in kwargs
        if expected:
            if type(expected) is set:
                assert set(kwargs['value']) == expected
            else:    
                assert kwargs['value'] == expected
        
    # cb returns {'value': <calvin.requests.calvinresponse.CalvinResponse>, 'key': 'NO-SUCH-KEY'} 
    _storage.add_index("node/affiliation/owner/com.ericsson/me", 'foo', 
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=200))
    _storage.add_index("node/affiliation/owner/com.ericsson/you", 'bar', 
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=200))
    # cb returns {'value': <list>}
    _storage.get_index("node/affiliation/owner/com.ericsson/me",         
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=['foo']))
    _storage.get_index("node/affiliation/owner/com.ericsson/you",         
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=['bar']))
    _storage.get_index("node/affiliation/owner/com.ericsson",         
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=set(['foo', 'bar'])))
    # cb returns  {'key': 'NO-SUCH-KEY', 'value': CalvinResponse(status=200)}
    _storage.remove_index("node/affiliation/owner/com.ericsson/you", 'baz', 
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=200))
    _storage.remove_index("node/affiliation/owner/com.ericsson/you", 'bar', 
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=200))
    _storage.get_index("node/affiliation/owner/com.ericsson",         
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=set(['foo'])))
    _storage.remove_index("node/affiliation/owner/com.ericsson", 'foo', 
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=200))
    _storage.get_index("node/affiliation/owner/com.ericsson",         
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=set(['foo'])))
    _storage.remove_index("node/affiliation/owner/com.ericsson/me", 'foo', 
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=200))
    _storage.get_index("node/affiliation/owner/com.ericsson",         
        root_prefix_level=2, 
        cb=CalvinCB(cb, expected=set()))
    with pytest.raises(NotImplementedError):
        _storage.delete_index("node/affiliation/owner/com.ericsson")
        

# get_index_iter(self, index, include_key=False, root_prefix_level=None):
# """
# Get multiple values from the registry stored at the index level or
# below it in hierarchy.
# index: The multilevel key:
#        a string with slash as delimiter for finer level of index,
#        e.g. node/address/example_street/3/buildingA/level3/room3003,
#        node/affiliation/owner/com.ericsson/Harald,
#        node/affiliation/name/com.ericsson/laptop,
#        index string must been escaped with \/ and \\ for / and \ within levels
#        OR a list of each levels strings
# include_key: When the parameter include_key is True a tuple of (index, value)
#        is placed in dynamic interable instead of only the retrived value,
#        note it is only the supplied index, not for each sub-level.
# returned: Dynamic iterable object
#     Values are placed in the dynamic iterable object.
#     The dynamic iterable are of the List subclass to
#     calvin.common.dynops.DynOps, see DynOps for details
#     of how they are used. The final method will be called when
#     all values are appended to the returned dynamic iterable.
# """
    

@pytest.mark.skipif(reason="Can't test this without async support")
def test_get_index_iter(_storage):
    _storage.add_index("node/affiliation/owner/com.ericsson/me", 'foo',
        root_prefix_level=2,
        cb=None)
    _storage.add_index("node/affiliation/owner/com.ericsson/you", 'bar',
        root_prefix_level=2,
        cb=None)
    it = _storage.get_index_iter("node/affiliation/owner/com.ericsson")
    value = next(it)
    assert value in ['foo', 'bar']
    value = next(it)
    assert value in ['foo', 'bar']
    with pytest.raises(Exception) as exc_info:
        value = next(it)
    assert exc_info.type in [StopIteration, dynops.PauseIteration]

    it = _storage.get_index_iter("node/affiliation/owner/com.ericsson",
        include_key=True)
    value = next(it)
    assert value in [
        ('node/affiliation/owner/com.ericsson', 'foo'),
        ('node/affiliation/owner/com.ericsson', 'bar')
    ]
    value = next(it)
    assert value in [
        ('node/affiliation/owner/com.ericsson', 'foo'),
        ('node/affiliation/owner/com.ericsson', 'bar')
    ]
    with pytest.raises(Exception) as exc_info:
        value = next(it)
    assert exc_info.type in [StopIteration, dynops.PauseIteration]
    


