# -*- coding: utf-8 -*-

import pytest

from calvin.common.attribute_resolver import AttributeResolver, format_index_string
from calvin.common import attribute_resolver

@pytest.fixture(scope="function")
def attributes():
    attrs = {
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
        },
        "public": {
            "profile": "Chaotic good"
        },
        "private": {
            "identity": {
                "name": "P. Parker",
                "job": "super hero"
            }
        }
    }
    return attrs


def test_empty_attributes():
    att = AttributeResolver({})
    assert att.get_private() == {}
    assert att.get_public() == {}
    assert att.get_indexed_public() == []
    assert att.get_node_name_as_str() is None


def test_attributes(attributes):
    att = AttributeResolver(attributes)
    assert att.get_private() == {'identity': {'job': 'super hero', 'name': 'P. Parker'}}
    assert att.get_public() == {'profile': 'Chaotic good'}
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


def test_get_private(attributes):
    att = AttributeResolver(attributes)
    assert att.get_private('identity') == {'job': 'super hero', 'name': 'P. Parker'}
    assert att.get_private('identity/job') == 'super hero'
    assert att.get_private('identity/job/level') is None
    assert att.get_private('identity/address') == {}
    assert att.get_private('profile') == {}


def test_get_public(attributes):
    att = AttributeResolver(attributes)
    assert att.get_public('identity') == {}
    assert att.get_public('identity/job') == {}
    assert att.get_public('profile') == 'Chaotic good'
    assert att.get_public('profile/interests') is None


def test_format_index_string():
    s = format_index_string({"owner": {"organization": "org.testexample", "personOrGroup": "testOwner1"}})
    assert s == "/node/attribute/owner/org.testexample///testOwner1"
    s = format_index_string({"owner": {"organization": "org.testexample"}})
    assert s == "/node/attribute/owner/org.testexample"
    s = format_index_string({"owner": {}})
    assert s == "/node/attribute/owner"


def test_format_index_string_trim():
    data = {"owner": {"organization": "org.testexample", "personOrGroup": "testOwner1"}}
    s = format_index_string(data, trim=False)
    assert s == "/node/attribute/owner/org.testexample///testOwner1"
    assert s == format_index_string(data, trim=True)

    s = format_index_string({"owner": {"organization": "org.testexample"}}, trim=False)
    assert s == "/node/attribute/owner/org.testexample///"

    s = format_index_string({"owner": {}}, trim=False)
    assert s == "/node/attribute/owner////"


def test_resolve_indexed_public():
    att = AttributeResolver({})
    data = att.resolve_indexed_public({"owner": {"organization": "org.testexample", "personOrGroup": "testOwner1"}})
    assert data == {'owner': ['org.testexample', '', '', 'testOwner1']}
    data = att.resolve_indexed_public({"owner": {"organization": "org.testexample"}})
    assert data == {'owner': ['org.testexample', '', '', '']}


def test_encode_decode_index():
    s = attribute_resolver.encode_index(['a1', 'å2', 'ö3'])
    assert s == "/node/attribute/a1/å2/ö3"
    assert attribute_resolver.decode_index(s) == ['a1', 'å2', 'ö3']


@pytest.mark.xfail(reason="Make decision if escaped chars should be allowed in index")
def test_escaped_encode_decode_index():
    s = attribute_resolver.encode_index(['a/1', 'a\\2', 'a3'])
    assert s == "/node/attribute/a\/1/a\\2/a3"
    assert attribute_resolver.decode_index(s) == ['a/1', 'a\\2', 'a3']

    s = attribute_resolver.encode_index(['a1/', '', 'a2\\', 'a3'])
    assert s == "/node/attribute/a1\///a2\\/a3"
    assert attribute_resolver.decode_index(s) == ['a1/', '', 'a2\\', 'a3']


def test_get_indexed_public_with_keys(attributes):
    att = AttributeResolver({})
    assert att.get_indexed_public_with_keys() == {}

    att = AttributeResolver(attributes)
    data = att.get_indexed_public_with_keys()
    assert len(data) == 10
    assert data["address.street"] == "Sölvegatan"
    assert data["address.streetNumber"] == "53"


def test_get_attribute(attributes):
    att = AttributeResolver(attributes)
    assert att._get_attribute(index="", which="public") == {'profile': 'Chaotic good'}
    expected = 'Chaotic good'
    assert att._get_attribute(index="profile", which="public") == expected
    assert att._get_attribute(index="/profile", which="public") == expected
    assert att._get_attribute(index="//profile", which="public") == expected
    assert att._get_attribute(index="///profile", which="public") == expected
    assert att._get_attribute(index="//profile/", which="public") == expected
    assert att._get_attribute(index="/profile//", which="public") == expected
    assert att._get_attribute(index="profile///", which="public") == expected

    assert att._get_attribute(index="", which="private") == {'identity': {'job': 'super hero', 'name': 'P. Parker'}}
    expected = {'job': 'super hero', 'name': 'P. Parker'}
    assert att._get_attribute(index="identity", which="private") == expected
    assert att._get_attribute(index="/identity", which="private") == expected
    assert att._get_attribute(index="//identity", which="private") == expected
    assert att._get_attribute(index="///identity", which="private") == expected
    assert att._get_attribute(index="//identity/", which="private") == expected
    assert att._get_attribute(index="/identity//", which="private") == expected
    assert att._get_attribute(index="identity///", which="private") == expected
    expected = 'super hero'
    assert att._get_attribute(index="identity/job", which="private") == expected
    assert att._get_attribute(index="/identity/job", which="private") == expected
    assert att._get_attribute(index="//identity/job", which="private") == expected
    assert att._get_attribute(index="///identity/job", which="private") == expected
    assert att._get_attribute(index="identity//job", which="private") == expected
    assert att._get_attribute(index="identity///job", which="private") == expected
    assert att._get_attribute(index="identity//job//", which="private") == expected


def test_has_attribute(attributes):
    att = AttributeResolver(attributes)
    assert att._has_attribute(index="", which="public")
    assert att._has_attribute(index="profile", which="public")
    assert att._has_attribute(index="/profile", which="public")
    assert att._has_attribute(index="//profile", which="public")
    assert att._has_attribute(index="///profile", which="public")
    assert att._has_attribute(index="//profile/", which="public")
    assert att._has_attribute(index="/profile//", which="public")
    assert att._has_attribute(index="profile///", which="public")
    assert att._has_attribute(index="", which="private")
    assert att._has_attribute(index="identity", which="private")
    assert att._has_attribute(index="/identity", which="private")
    assert att._has_attribute(index="//identity", which="private")
    assert att._has_attribute(index="///identity", which="private")
    assert att._has_attribute(index="//identity/", which="private")
    assert att._has_attribute(index="/identity//", which="private")
    assert att._has_attribute(index="identity///", which="private")
    assert att._has_attribute(index="identity/job", which="private")
    assert att._has_attribute(index="/identity/job", which="private")
    assert att._has_attribute(index="//identity/job", which="private")
    assert att._has_attribute(index="///identity/job", which="private")
    assert att._has_attribute(index="identity//job", which="private")
    assert att._has_attribute(index="identity///job", which="private")
    assert att._has_attribute(index="identity//job//", which="private")
    assert not att._has_attribute(index="address", which="public")

    assert not att._has_attribute(index="address", which="random")


def test_abuse(attributes):
    att = AttributeResolver(attributes)
    assert att._has_attribute(index="", which="indexed_public")
    assert att._has_attribute(index="address", which="indexed_public")
    assert att._has_attribute(index="address/streetNumber", which="indexed_public") is None
    
def test_address_resolver():
    # Good case
    data = attribute_resolver.address_resolver({"country": "SE", "stateOrProvince": "Skåne"})
    assert data == ['SE', 'Skåne', '', '', '', '', '', '']
    # Lower case country
    data = attribute_resolver.address_resolver({"country": "se"})
    assert data == ['SE', '', '', '', '', '', '', '']
    # Bad country
    with pytest.raises(Exception):
        attribute_resolver.address_resolver({"country": "SF"})
    # Bad stateOrProvince
    with pytest.raises(Exception):
        attribute_resolver.address_resolver({"stateOrProvince": "Skåne"})
