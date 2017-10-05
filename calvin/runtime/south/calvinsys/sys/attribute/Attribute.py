
# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from calvin.runtime.south.calvinsys import base_calvinsys_object

class Attribute(base_calvinsys_object.BaseCalvinsysObject):
    """
    Attribute - Fetching runtime attributes. Uses dot-notation for attributes, i.e. address.locality not /address/locality.
    
    Note: private attributes _can_ be exposed, but probably should not be.
    """

    init_schema = {
        "description": "Set up attribute module",
        "properties" : {
            "type" :  {
                "description": "Type of attribute to get",
                "enum": ["public", "private", "indexed"]
            }
        },
        "required": ["type"]
    }
    
    can_read_schema = {
        "description": "True if attribute has been set and exists in current runtime",
        "type": "boolean"
    }


    write_schema = {
        "description": "Select attribute to read",
        "properties": {
            "attribute": {
                "type": "string",
                "pattern": "^[^.]+(\.[^.]+)*$"
            }
        }
    }

    read_schema = {
        "description":  "Read value of selected attribute",
        "type": ["string", "object", "number"]
    }

    def init(self, **kwargs):
        self._type = kwargs["type"]
        self._attribute = None

    def write(self, attribute):
        self._attribute = attribute
        # public and private attributes use path notation
        if self._type in ["private", "public"]:
            self._attribute = attribute.replace('.', '/')

    def _has_attribute(self):
        val = None
        if self._type == "private":
            val = self.calvinsys._node.attributes.has_private_attribute(self._attribute)
        elif self._type == "public":
            val = self.calvinsys._node.attributes.has_public_attribute(self._attribute)
        elif self._type == "indexed":
            val = self._attribute in self.calvinsys._node.attributes.get_indexed_public_with_keys()
        
        return bool(val)
        
    def _get_attribute(self):
        val = None
        if self._type == "private":
            val = self.calvinsys._node.attributes.get_private(self._attribute)
        elif self._type == "public":
            val = self.calvinsys._node.attributes.get_public(self._attribute)
        elif self._type == "indexed":
            val = self.calvinsys._node.attributes.get_indexed_public_with_keys().get(self._attribute)
        return val

    def can_read(self):
        return self._attribute is not None and self._has_attribute()
        
    def read(self):
        return self._get_attribute()
    
    def close(self):
        pass

    def serialize(self):
        return {"attribute": self._attribute, "type": self._type}
        
    def deserialize(self, state, **kwargs):
        self._type = state["type"]
        self._attribute = state["attribute"]
        return self
