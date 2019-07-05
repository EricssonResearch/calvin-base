# -*- coding: utf-8 -*-

import unittest
import pytest

from calvin.common.attribute_resolver import AttributeResolver, format_index_string
from calvin.common import attribute_resolver


def test_empty_attr():
    att = AttributeResolver({})
    assert att.get_private() == {}
    assert att.get_public() == {}
    assert att.get_indexed_public() == []
    assert att.get_node_name_as_str() == None
    
def test_attr():
    attributes = {
        "indexed_public": {
            "address": {
                "country": "SE", 
                "locality": "Lund", 
                "street": "Sölvegatan", 
                "streetNumber": 53
            },
            "owner": {
                "organization": "ericsson.com", 
                "organizationalUnit": "Ericsson Research", 
                "personOrGroup": "CT"
            },
            "node_name": {
                "organization": "ericsson.com", 
                "purpose": "Test", 
                "name": "alpha1"
            }
        }
    }
    att = AttributeResolver(attributes)
    assert att.get_private() == {}
    assert att.get_public() == {}
    assert att.get_indexed_public() == [
        '/node/attribute/address/SE//Lund/Sölvegatan/53///',
        '/node/attribute/owner/ericsson.com/Ericsson Research//CT',
        '/node/attribute/node_name/ericsson.com//Test//alpha1'
    ]
    assert att.get_node_name_as_str() == "ericsson.com--Test--alpha1"
    attr_lists = att.get_indexed_public(as_list=True)
    assert len(attr_lists) == 3
    assert len(attr_lists[0]) == 11
    assert len(attr_lists[1]) == 7
    assert len(attr_lists[2]) == 8
    assert attr_lists[0][3] == 'SE'
    assert attr_lists[0][4] == ''
    assert attr_lists[0][7] == '53'
    
def test_format_index_string():
    s = format_index_string({"owner": {"organization": "org.testexample", "personOrGroup": "testOwner1"}})
    assert s == "/node/attribute/owner/org.testexample///testOwner1"
    s = format_index_string({"owner": {"organization": "org.testexample"}})
    assert s == "/node/attribute/owner/org.testexample"
    s = format_index_string({"owner": {}})
    assert s == "/node/attribute/owner"
    
def test_resolve_indexed_public():
    att = AttributeResolver({})
    data = att.resolve_indexed_public({"owner": {"organization": "org.testexample", "personOrGroup": "testOwner1"}})
    assert data == {'owner': ['org.testexample', None, None, 'testOwner1']}
    data = att.resolve_indexed_public({"owner": {"organization": "org.testexample"}})
    assert data == {'owner': ['org.testexample', None, None, None]}
    
def test_encode_decode_index():
    s = attribute_resolver.encode_index(['a1', 'å2', 'ö3'])    
    assert s == "/node/attribute/a1/å2/ö3"
    assert attribute_resolver.decode_index(s) == ['a1', 'å2', 'ö3']
    
@pytest.mark.xfail(reason="Make decision if escaped chars should be allowed in index")
def test_escaped_encode_decode_index():
    s = attribute_resolver.encode_index(['a/1', 'a\\2', 'a3'])
    assert s == "/node/attribute/a\/1/a\\2/ö3"
    assert attribute_resolver.decode_index(s) == ['a/1', 'a\\2', 'a3']

    s = attribute_resolver.encode_index(['a1/', '', 'a2\\', 'a3'])
    assert s == "/node/attribute/a1\///a2\\/a3"
    assert attribute_resolver.decode_index(s) == ['a1/', '', 'a2\\', 'a3']
    
