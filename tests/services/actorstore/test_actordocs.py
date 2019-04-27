import json

import pytest

from tools import toolsupport

@pytest.fixture(scope='module')
def docstore():
    """Local DocumentationStore instance"""
    ts = toolsupport.ToolSupport('local')
    return ts

def test_sanity(docstore):
    assert docstore

def test_help_root_arg_none(docstore):
    actual = docstore.help(what=None, compact=True, formatting='plain')
    assert "Module: /" == actual[:9]

def test_help_root_arg_empty_string(docstore):
    actual = docstore.help(what="", compact=True, formatting='plain')
    assert "Module: /" == actual[:9]

def test_help_raw_root_arg_none(docstore):
    actual = json.loads(docstore.help_raw(what=None))
    assert actual['type'] == 'module'
    assert actual['name'] == '/'
    assert actual['items']

def test_help_raw_root_arg_empty_string(docstore):
    actual = json.loads(docstore.help_raw(what=""))
    assert actual['type'] == 'module'
    assert actual['name'] == '/'
    assert actual['items']

def test_help_raw_flow(docstore):
    actual = json.loads(docstore.help_raw(what='flow'))
    assert actual['type'] == 'module'
    assert actual['name'] == 'flow'
    assert [x for x in actual['items'] if x['name'] == 'Init']

def test_help_raw_flow_init(docstore):
    actual = json.loads(docstore.help_raw('flow.Init'))
    assert actual['is_known']
    assert 'sys.schedule' in actual['requires']

def test_help_raw_unknown(docstore):
    actual = json.loads(docstore.help_raw(what='no_such_thing'))
    assert actual['documentation'] == ['Unknown module']
    
def test_help_raw_qualified_unknown(docstore):
    actual = json.loads(docstore.help_raw(what='no.such.thing'))
    assert actual['documentation'] == ['Unknown actor']

