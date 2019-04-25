import pytest

from calvinservices.csparser.metadata_proxy import ActorMetadataProxy

script = """
component Filter(param) in -> out {
    id : std.Identity()
    
    .in > id.token
    id.token > .out
}

src : flow.Init(data=1)
filt : Filter(param=1)
snk : foo.Bar()

voidport > src.in
src.out > filt.in
filt.out > snk.token
"""

system_config = r"""
- class: ACTORSTORE
  name: actorstore
  port: 4999
  type: REST
"""

params = [
    # (config, script|None, expect_idx)
    (None, None, 0),
    (None, script, 1),
    ('local', None, 2),
    ('local', script, 3),
    ('remote', None, 2),
    ('remote', script, 3),
]


@pytest.fixture(params=params, ids=lambda x: str(x[0]) + ('+script' if x[1] else ''))
def mdproxy(request, system_setup):
    actorstore_uri = system_setup['actorstore']['uri']
    config, script, expect_idx = request.param
    cfg = actorstore_uri if config == 'remote' else config
    mdproxy = ActorMetadataProxy(config=cfg, source_text=script)
    yield(mdproxy, expect_idx)

testlist = [
    ('',          'module',     '/',     (False, False, False, False)), 
    ('std',       'module',    'std',    (False, False, False, False)), 
    ('flow.Init', 'actor',     'Init',   (False, False, True,  True )),
    ('foo.Bar',   'actor',     'Bar',    (False, False, False, False)),
    ('Bar',       'component', 'Bar',    (False, False, False, False)),
    ('Filter',    'component', 'Filter', (False, True,  False, True )),
]
    
@pytest.mark.parametrize('test', testlist, ids=lambda x: '-'.join(x[:2]))
def test_metadata(mdproxy, test):
    proxy, expect_idx = mdproxy
    query, type_, name, known = test
    # Access store directly, may return None
    md = proxy.store.get_metadata(query)
    assert md is None or isinstance(md, dict)
    md = proxy.get_metadata(query)
    # Access store via proxy, should return dict
    assert isinstance(md, dict)
    # print(md)
    assert md['type'] == type_
    assert md['name'] == name
    assert md.get('is_known', False) == known[expect_idx]


testlist2 = [
    ('',          (True, True, True,  True )), 
    ('std',       (True, True, True,  True )), 
    ('flow.Init', (True, True, False, False)),
    ('foo.Bar',   (True, True, True,  True )),
    ('Bar',       (True, True, True,  True )),
    ('Filter',    (True, True, True,  True )),
]
    
@pytest.mark.parametrize('test', testlist2, ids=lambda x: x[0])
def test_source(mdproxy, test):
    proxy, expect_idx = mdproxy
    query, isNone = test
    src = proxy.get_source(query)
    assert (src is None) == isNone[expect_idx]

def test_known_actor(system_setup):
    actorstore_uri = system_setup['actorstore']['uri']
    proxy = ActorMetadataProxy(config=actorstore_uri)
    md = proxy.get_metadata('flow.Init')
    assert {'direction': 'in', 'help': 'Any token', 'name': 'in'} in md['ports']
    assert md['requires'] == ['sys.schedule']
    
def test_locally_defined_component():
    proxy = ActorMetadataProxy(config=None, source_text=script)
    md = proxy.get_metadata('Filter')
    print(md)
    assert {'direction': 'out', 'name': 'out'} in md['ports']
    assert {'direction': 'in', 'name': 'in'} in md['ports']
    assert md['args'] == [{'mandatory': True, 'name': 'param'}]
