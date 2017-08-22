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


class StandardOut(base_calvinsys_object.BaseCalvinsysObject):
    """
    StandardOut 
    """

    init_schema = {
        "type": "object",
        "properties": {
            "prefix": {
                "description": "String to prefix all data",
                "type": "string"
            }
        },
        "description": "Send all incoming data to terminal (usually not very useful)"
    }

    can_write_schema = {
        "description": "Always true",
        "type": "boolean"
    }

    write_schema = {
        "description": "Write data to standard out",
        "type": ["boolean", "integer", "number", "string", "array", "object", "null"]
    }

    def init(self, prefix=None, **kwargs):
        self._prefix = prefix

    def can_write(self):
        return True

    def write(self, data=None):
        msg = ""
        if data and self._prefix:
            msg = "{}: {}".format(self._prefix, data)
        elif data:
            msg = "{}".format(data)
            pass
        elif self._prefix:
            msg = "{}".format(self._prefix)
        print(msg)

    def close(self):
        pass

