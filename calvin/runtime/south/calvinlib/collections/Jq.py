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
import pyjq

class Jq(base_calvinlib_object.BaseCalvinlibObject):
    """
    Functions for manipulating JSON typed collections, e.g. lists, dicts, etc, input/output is NOT JSON-string.
    Requires the pyjq python package, which requires the autoconf automake libtool due to source code package
    These could be installed using e.g. 
    mac: brew install autoconf automake libtool
    debian: apt-get install autoconf automake build-essential libtool python-dev
    all: pip install pyjq
    """

    init_schema = {
            "description": "setup jq manipulation functions"
    }
    
    all_schema = {
        "description": "Transform value by script, returning all results as list.",
        "type": "object",
        "properties": {
            "script": {
                "description": "jq script",
                "type": "string"
            },
            "value": {
                "description": "Object to be transformed",
                "type": "object"
            },
            "vars": {
                "description": "Dictionary with variables to be substituted in the script",
                "type": "object"
            }
        }
    }
    
    first_schema = {
        "description": "Transform object by jq script, returning the first result. Return default if result is empty.",
        "type": "object",
        "properties": {
            "script": {
                "description": "jq script",
                "type": "string"
            },
            "value": {
                "description": "Object to be transformed",
                "type": "object"
            },
            "vars": {
                "description": "Dictionary with variables to be substituted in the script",
                "type": "object"
            }
        }
    }

    one_schema = {
        "description": "Transform object by jq script, returning the first result. Raise Exceptino unless results does not include exactly one element.",
        "type": "object",
        "properties": {
            "script": {
                "description": "jq script",
                "type": "string"
            },
            "value": {
                "description": "Object to be transformed",
                "type": "object"
            },
            "vars": {
                "description": "Dictionary with variables to be substituted in the script",
                "type": "object"
            }
        }
    }

    compile_schema = {
        "description": "Compile a jq script, returning a script object.",
        "type": "object",
        "properties": {
            "script": {
                "description": "jq script",
                "type": "string"
            },
            "vars": {
                "description": "Dictionary with variables to be substituted in the script",
                "type": "object"
            }
        }
    }

    def init(self):
        pass

    def all(self, script, value, vars={}):
        return pyjq.all(script, value, vars=vars)

    def first(self, script, value, vars={}):
        return pyjq.first(script, value, vars=vars)

    def one(self, script, value, vars={}):
        return pyjq.one(script, value, vars=vars)

    def compile(self, script, vars={}):
        return pyjq.compile(script, vars)

