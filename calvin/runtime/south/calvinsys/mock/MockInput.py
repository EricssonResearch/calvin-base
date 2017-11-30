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


class MockInput(base_calvinsys_object.BaseCalvinsysObject):
    """
    MockInput - Mocked input device.
    """

    init_schema = {
        "type": "object",
        "properties": {
            "data": {
                "description": "Data to return in read",
                "type": "array"
            }
        }
    }

    can_read_schema = {
        "description": "Returns True if data can be read, otherwise False",
        "type": "boolean"
    }

    read_schema = {
        "description": "Get data, verifies that can_read has been called."
    }

    can_write_schema = {
        "description": "Always returns True",
        "type": "boolean"
    }

    write_schema = {
        "description": "Any data"
    }

    def init(self, data, **kwargs):
        self.read_called = False
        self._read_allowed = True

        calvinsys = kwargs.get('calvinsys', '')
        if 'read' in calvinsys:
            self.data = calvinsys['read']
        else:
            self.data = list(data)

    def can_read(self):
        self._read_allowed = True
        return len(self.data) > 0

    def read(self):
        self.read_called = True
        if not self._read_allowed:
            raise AssertionError("read() called without preceding can_read()")
        self._read_allowed = False
        return self.data.pop(0)

    def can_write(self):
        return True

    def write(self, data):
        pass

    def close(self):
        self.data = []

    def start_verifying_calvinsys(self):
        self._read_allowed = False
