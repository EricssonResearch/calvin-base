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
import re


class PyRegexp(base_calvinlib_object.BaseCalvinlibObject):
    """
    Python-based regular expressions - (currently limited functionality)

    Note: See documentation for python re module for details
    """

    findall_schema = {
        "description": "Find all occurrences matching 'pattern' as per python re.findall()",
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "string": {"type": "string"}
        }
    }

    match_schema = {
        "description": "Match pattern with start of string as per python re.match().",
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "string": {"type": "string"}
        }

    }

    def init(self):
        pass

    def findall(self, pattern, string):
        return re.findall(pattern, string)

    def match(self, pattern, string):
        return re.match(pattern, string)
