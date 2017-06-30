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

from calvin.runtime.south.calvinlib import base_calvinlib_object
import json

class Json(base_calvinlib_object.BaseCalvinlibObject):
    """
    Functions for manipulating JSON.
    """

    init_schema = {
            "description": "setup json manipulation functions"
    }
    
    tostring_schema = {
        "description": "convert json structure into string",
        "type": "object"
        
    }
    
    fromstring_schema = {
        "description": "convert string representation of json structure into structure",
        "type": "string"
    }

    def init(self):
        pass
    
    def tostring(self, structure):
        return json.dumps(structure)

    def fromstring(self, string):
        return json.loads(string)


