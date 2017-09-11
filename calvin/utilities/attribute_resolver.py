# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# import copy
import re

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

# The order of the address fields
address_keys = ["country", "stateOrProvince", "locality", "street", "streetNumber", "building", "floor", "room"]
address_help = {"country": 'ISO 3166-1 alpha2 coded country name string',
                "stateOrProvince": 'ISO 3166-2 coded sub-country name string',
                "locality": 'Name of e.g. city',
                "street": 'Street name',
                "streetNumber": 'String or number for street number',
                "building": 'Some buildings have names (maybe instead of number)',
                "floor": 'String or number specifying floor of building',
                "room": 'String or number specifying room or flat name'}
# The order of the owner fields
owner_keys = ["organization", "organizationalUnit", "role", "personOrGroup"]
owner_help = {"organization": '(reversed DNS) name of organisation',
              "organizationalUnit": 'Sub-unit name',
              "role": 'The title of owner e.g. "Site owner", "admin"',
              "personOrGroup": 'The name of the owner(s), e.g. person name or responsible group name'}
# The order of the node name fields, purpose field could take values such as test, production, etc
node_name_keys = ["organization", "organizationalUnit", "purpose", "group", "name"]
node_name_help = {"organization": '(reversed DNS) name of organisation',
                  "organizationalUnit": 'Sub-unit name',
                  "purpose": 'If specific purpose of node, e.g. test, production',
                  "group": 'Name of node group e.g. "project" name',
                  "name": 'Name of node'}
# Acceptable values for CPU parameter
cpuAvail_keys =  ["0", "25", "50", "75", "100"]
cpuAvail_help = {"0": "No CPU available",
                 "25": "25% of CPU available",
                 "50": "50% of CPU available",
                 "75": "75% of CPU available",
                 "100":"100% of CPU available"}

cpuAffinity_keys = ["dedicated"]
cpuAffinity_help = {"dedicated": "Runs in a unique CPU"}

cpuTotal_keys = ["1", "1000", "100000", "1000000", "10000000"]
cpuTotal_help = {"1": "One MIPS",
                 "1000": "One thousand MIPS",
                 "100000": "One hundred thousand MIPS",
                 "1000000": "One GIPS (billion instructions per second)",
                 "10000000":"Ten GIPS (billion instructions per second)"}

# Acceptable values for RAM parameter
memAvail_keys =  ["0", "25", "50", "75", "100"]
memAvail_help = {"0": "No RAM available",
                 "25": "25% of RAM available",
                 "50": "50% of RAM available",
                 "75": "75% of RAM available",
                 "100":"100% of RAM available"}

memTotal_keys = ["1K", "100K", "1M", "100M", "1G", "10G"]
memTotal_help = {"1K": "1Kb of RAM",
                 "100K": "100Kb of RAM",
                 "1M": "1Mb of RAM",
                 "100M": "100Mb of RAM",
                 "1G":"1Gb of RAM",
                 "10G":"10Gb of RAM"}


# list of acceptable resources
resource_list = ["cpuAvail", "memAvail"]

attribute_docs = '''
# Calvin Node Attributes
Command line tool csruntime take the node attribute data in JSON coded form, either on the line or as a file.

    csruntime -n localhost --attr-file test_attr.json
    csruntime -n localhost --attr '{"indexed_public": {"owner": {"personOrGroup": "Me"}}}'

The python functions start_node and dispatch_node takes the attributes as a python object.

The data structure is as follows:

    {
        "public": # Any public info stored in storage when requesting the node id
                { # TODO fomalize these values, e.g. public key
                },
        "private": # Any configuration of the node that is NOT in storage only kept in node
                { # TODO formalize these values, e.g. private key
                },
        "indexed_public": # Any public info that is also searchable by the index, also in storage with node id
                          # The index is prefix searchable by higher level keywords. It is OK to skip levels.
                          # This list is formal and is intended to be extended as needed
                {
'''
_indent_index = 20
_indent_index2 = _indent_index + 4
attribute_docs += ' ' * _indent_index + '"owner": {# The node\'s affilation\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + owner_help[a] for a in owner_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '"address": {# The node\'s (static) address\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + address_help[a] for a in address_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '"node_name": { # The node\'s static easy identification\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + node_name_help[a] for a in node_name_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '"cpuTotal": { # The node\'s CPU power in MIPS (million instructions per second)\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + cpuTotal_help[a] for a in cpuTotal_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '"cpuAvail": { # The node\'s CPU availability information\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + cpuAvail_help[a] for a in cpuAvail_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '"cpuAffinity": { # The node\'s CPU affinity\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + cpuAffinity_help[a] for a in cpuAffinity_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '"memTotal": { # The node\'s total RAM information\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + memTotal_help[a] for a in memTotal_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '"memAvail": { # The node\'s RAM availability information\n'
attribute_docs += (',\n').join([' ' * _indent_index2 + '"' + a + '": ' + memAvail_help[a] for a in memAvail_keys]) + '\n' + ' ' * _indent_index + '},\n'
attribute_docs += ' ' * _indent_index + '''"user_extra": {# Any user specific extra attributes, as a list of list with index words, not possible to skip levels
                }
    }

The public indexed values can be obtained by get_index function or the corresponding control API.

To format the index search string an attribute resolver function needs to be used:

    from calvin.utilities.attribute_resolver import format_index_string
    format_index_string(attr_obj, trim=True)

where the attr_obj should only contain ONE attribute e.g.

    {"owner": {"organization": "org.testorg", "role": "admin"}}

alternatively the attr is a tuple e.g.:

    ("owner", {"organization": "org.testorg", "role": "admin"})

The trim parameter when true will remove trailing empty keys instead of leaving them empty, this allows the
prefix search to find nodes based only on the included higher level keys.
'''

# Country codes
countries = ["AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ", "BA",
             "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV",
             "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO", "CR", "CU",
             "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES",
             "ET", "FI", "FJ", "FK", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL", "GM",
             "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR", "HT", "HU", "ID", "IE",
             "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM",
             "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY",
             "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK", "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT",
             "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU",
             "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM", "PN", "PR", "PS", "PT", "PW", "PY", "QA",
             "RE", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM",
             "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL",
             "TM", "TN", "TO", "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE",
             "VG", "VI", "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW"]



class AttributeResolverHelper(object):
    '''Resolves attributes'''

    @staticmethod
    def _to_unicode(value):
        if isinstance(value, str):
            return value.decode("UTF-8")
        elif isinstance(value, unicode):
            return value
        else:
            return str(value).decode("UTF-8")

    @classmethod
    def owner_resolver(cls, attr):
        if not isinstance(attr, dict):
            raise Exception('Owner attribute must be a dictionary with %s keys.' % owner_keys)
        resolved = [cls._to_unicode(attr[k]) if k in attr.keys() else None for k in owner_keys]
        return resolved

    @classmethod
    def node_name_resolver(cls, attr):
        if not isinstance(attr, dict):
            raise Exception('Node name attribute must be a dictionary with %s keys.' % node_name_keys)
        resolved = [cls._to_unicode(attr[k]) if k in attr.keys() else None for k in node_name_keys]
        return resolved

    @classmethod
    def address_resolver(cls, attr):
        if not isinstance(attr, dict):
            raise Exception('Address attribute must be a dictionary with %s keys.' % address_keys)
        if "country" in attr:
            attr["country"] = attr["country"].upper()
            if attr["country"] not in countries:
                raise Exception("country must be ISO 3166-1 alpha2")
        if "stateOrProvince" in attr and "country" not in attr:
            raise Exception("country required for stateOrProvince, see ISO 3166-2 for proper code")
        resolved = [cls._to_unicode(attr[k]) if k in attr.keys() else None for k in address_keys]
        return resolved

    @classmethod
    def cpu_avail_resolver(cls, attr):
        if attr not in cpuAvail_keys:
            raise Exception('CPU availability must be: %s' % cpuAvail_keys)
        resolved = map(cls._to_unicode, cpuAvail_keys[:cpuAvail_keys.index(attr) + 1])
        return resolved

    @classmethod
    def cpu_total_resolver(cls, attr):
        if attr not in cpuTotal_keys:
            raise Exception('CPU power must be: %s' % cpuTotal_keys)
        resolved = map(cls._to_unicode, cpuTotal_keys[:cpuTotal_keys.index(attr) + 1])
        return resolved

    @classmethod
    def cpu_affi_resolver(cls, attr):
        if attr not in cpuAffinity_keys:
            raise Exception('CPU affinity must be: %s' % cpuAffinity_keys)
        resolved = [cls._to_unicode(attr)]
        return resolved

    @classmethod
    def mem_avail_resolver(cls, attr):
        if attr not in memAvail_keys:
            raise Exception('RAM availability must be: %s' % memAvail_keys)
        resolved = map(cls._to_unicode, memAvail_keys[:memAvail_keys.index(attr) + 1])
        return resolved

    @classmethod
    def mem_total_resolver(cls, attr):
        if attr not in memTotal_keys:
            raise Exception('RAM must be: %s' % memTotal_keys)
        resolved = map(cls._to_unicode, memTotal_keys[:memTotal_keys.index(attr) + 1])
        return resolved

    @classmethod
    def extra_resolver(cls, attr):
        if isinstance(attr, list) and attr and isinstance(attr[0], list):
            return attr
        else:
            raise Exception('User extra attribute must be a list of ordered attribute lists.')

    @staticmethod
    def encode_index(attr, as_list=False):
        if not set(attr).isdisjoint(resource_list):
            attr_str = '/node/resource'
            attr_list = [u'node', u'resource']
        else:
            attr_str = '/node/attribute'
            attr_list = [u'node', u'attribute']

        for a in attr:
            if a is None:
                a = ''
            else:
                # Replace \ with \\, looks funny due to \ is used to escape characters in python also
                a = a.replace('\\', '\\\\')
                # Replace / with \/
                a = a.replace('/', '\\/')
            attr_str += '/' + a
            attr_list.append(a)
        return attr_list if as_list else attr_str

    @staticmethod
    def decode_index(attr_str):
        if attr_str.startswith('/node/resource'):
            attr_str = attr_str[len('/node/resource') + 1:]
        elif attr_str.startswith('/node/attribute'):
            attr_str = attr_str[len('/node/attribute') + 1:]
        else:
            raise Exception('Index %s not a node attribute' % attr_str)

        attr = re.split(r"(?<![^\\]\\)/", attr_str)
        attr2 = []
        for a in attr:
            a = a.replace('\\/', '/')
            a = a.replace('\\\\', '\\')
            if a:
                attr2.append(a)
            else:
                attr2.append(None)
        return attr2


attr_resolver = {"owner": AttributeResolverHelper.owner_resolver,
                 "node_name": AttributeResolverHelper.node_name_resolver,
                 "address": AttributeResolverHelper.address_resolver,
                 "cpuTotal" : AttributeResolverHelper.cpu_total_resolver,
                 "cpuAvail" : AttributeResolverHelper.cpu_avail_resolver,
                 "cpuAffinity" : AttributeResolverHelper.cpu_affi_resolver,
                 "memAvail" : AttributeResolverHelper.mem_avail_resolver,
                 "memTotal" : AttributeResolverHelper.mem_total_resolver,
                 "user_extra": AttributeResolverHelper.extra_resolver}

keys = {"owner": owner_keys,
        "node_name": node_name_keys,
        "address": address_keys,
        "cpuTotal": cpuTotal_keys,
        "cpuAvail": cpuAvail_keys,
        "cpuAffinity": cpuAffinity_keys,
        "memAvail": memAvail_keys,
        "memTotal": memTotal_keys}

def format_index_string(attr, trim=True):
    ''' To format the index search string an attribute resolver function needs to be used:
        where the attr should only contain ONE attribute e.g.
            {"owner": {"organization": "org.testorg", "role":"admin"}}
        alternatively the attr is a tuple e.g.:
            ("owner", {"organization": "org.testorg", "role":"admin"})
        The trim parameter, when true, will remove trailing empty keys instead of leaving them empty.
        This allows the prefix search to find nodes based only on the included higher level keys.
    '''
    attr_type = None
    attribute = None
    if isinstance(attr, dict):
        attr_type, attribute = attr.iteritems().next()
    elif isinstance(attr, (list, tuple)):
        attr_type, attribute = attr[0], attr[1]
    _attr = attr_resolver[attr_type](attribute)
    if trim:
        _attr = [_attr[i] for i in range(len(_attr)) if any(_attr[i:])]
    return AttributeResolverHelper.encode_index([attr_type] + _attr)


class AttributeResolver(object):
    '''Resolves incoming attributes for a node and verify it'''
    def __init__(self, attr):
        super(AttributeResolver, self).__init__()
        self.attr = attr
        if self.attr is None:
            self.attr = {"indexed_public": {}, "public": {}, "private": {}}
        else:
            self.resolve()

    def __str__(self):
        return str(self.attr)

    def resolve(self):
        if not isinstance(self.attr, dict):
            raise Exception('Attributes must be a dictionary with "public", "private" and "indexed_public" keys.')
        self.attr["indexed_public"] = self.resolve_indexed_public(self.attr.get("indexed_public", None))
        # TODO resolve public and private fields
        if "public" not in self.attr:
            self.attr["public"] = {}
        if "private" not in self.attr:
            self.attr["private"] = {}

    def set_indexed_public(self, attributes):
        attr = {}
        for attr_type, attribute in attributes.items():
            attr[attr_type] = attr_resolver[attr_type](attribute)
        self.attr["indexed_public"] = attr

    def resolve_indexed_public(self, attr):
        if attr:
            for attr_type, attribute in attr.items():
                try:
                    attr[attr_type] = attr_resolver[attr_type](attribute)
                except Exception:
                    attr[attr_type] = []
            return attr
        else:
            return {}

    def _get_attribute_helper(self, indices, value):
        if indices == []:
            return value
        else:
            return self._get_attribute_helper(indices[1:], value[indices[0]])
    
    def _get_attribute(self, index, which):
        indices = [idx for idx in index.split("/") if idx] # remove extra /'s
        try:
            return self._get_attribute_helper(indices, self.attr[which])
        except KeyError:
            _log.warning("Warning: No such attribute '%r'" % (index,))
            return {}
        except:
            _log.error("Error: Invalid attribute '%r'" % (index,))

    def _has_attribute(self, index, which):
        indices = [idx for idx in index.split("/") if idx] # remove extra /'s
        try:
            return self._get_attribute_helper(indices, self.attr[which]) or True
        except KeyError:
            return False
        except:
            _log.error("Error: Invalid attribute '%r'" % (index,))
        
    def has_private_attribute(self, index):
        return self._has_attribute(index, "private")
        
    def has_public_attribute(self, index):
        return self._has_attribute(index, "public")
        
    def get_private(self, index=None):
        if not index:
            return self.attr["private"]
        return self._get_attribute(index, "private")            

    def get_public(self, index=None):
        if not index:
            return self.attr["public"]
        return self._get_attribute(index, "public")

    def get_indexed_public(self, as_list=False):
        # Return all indexes encoded for storage as a list of lists
        return [AttributeResolverHelper.encode_index([AttributeResolverHelper._to_unicode(k)] + v, as_list=as_list) for k, v in self.attr["indexed_public"].items()]

    def get_node_name_as_str(self):
        """
        Generate a string corresponding to the attribute node name.

        The sub-parts are concatenated by '+' to be able to use it as a filename.
        """
        try:
            return '-'.join(["" if i is None else i for i in self.attr['indexed_public']['node_name']])
        except:
            return None

    def get_indexed_public_with_keys(self):
        """
        Return a dictionary with all indexed_public attributes that have been set.

        The attribute type (e.g. "owner") and the attribute name (e.g. "organization")
        are concatenated using "." to form the key (e.g. "owner.organization").
        """
        return {attr_type + "." + keys[attr_type][i]: value 
                for attr_type, value_list in self.attr["indexed_public"].iteritems() 
                for i, value in enumerate(value_list) if value is not None}

if __name__ == "__main__":
    ar = AttributeResolver({"indexed_public": {
                            "address": {"country": "SE", "locality": "Lund", "street": u"Sölvegatan", "streetNumber": 53},
                            "owner": {"organization": u"ericsson.com", "organizationalUnit": "Ericsson Research", "personOrGroup": "CT"},
                            "node_name": {"organization": "ericsson.com", "purpose": "Test", "name": "alpha1"},
                            "cpuAvail": 50}})

    print attribute_docs

    s = AttributeResolverHelper.encode_index(['a1', 'a2', 'a3'])
    print s
    print AttributeResolverHelper.decode_index(s)
    s = AttributeResolverHelper.encode_index(['a/1', 'a\\2', 'ö3'])
    print s
    aa = AttributeResolverHelper.decode_index(s)
    print aa, 'correct?', aa[2]
    s = AttributeResolverHelper.encode_index(['a1/', '', 'a2\\', u'a3'])
    print s
    print AttributeResolverHelper.decode_index(s)
    aa = ar.get_indexed_public(as_list=True)
    print aa
    print aa[2][6]
    ar = AttributeResolver(None)
    aa = ar.get_indexed_public(as_list=True)
    print aa
    print ar.resolve_indexed_public({"owner": {"organization": "org.testexample", "personOrGroup": "testOwner1"}})
    print format_index_string({"owner": {"organization": "org.testexample", "personOrGroup": "testOwner1"}})
    print ar.resolve_indexed_public({"owner": {"organization": "org.testexample"}})
    print format_index_string({"owner": {"organization": "org.testexample"}})
    print format_index_string({"owner": {}})
    s = AttributeResolverHelper.encode_index(['cpuAvail', '0', '25', '50'])
    print s
    print AttributeResolverHelper.decode_index(s)
    
