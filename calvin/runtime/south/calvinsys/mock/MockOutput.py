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


class MockOutput(base_calvinsys_object.BaseCalvinsysObject):
    """
    MockOutput - Mocked output device printing data to stdout.
    """

    init_schema = {
        "description": "Init object"
    }

    can_write_schema = {
        "description": "Always returns True",
        "type": "boolean"
    }

    write_schema = {
        "description": "Compares data to expected data specified in actor test, also verifies that can_write has been called."
    }

    def init(self, **kwargs):
        self.write_called = False
        self._write_allowed = True
        self._expected_data = []

        calvinsys = kwargs.get('calvinsys', '')
        if 'write' in calvinsys:
            self._expected_data = calvinsys['write']

    def can_write(self):
        self._write_allowed = True
        return True

    def write(self, data):
        self.write_called = True
        if not self._write_allowed:
            raise AssertionError("write() called without preceding can_write()")
        self._write_allowed = False

        if self._expected_data:
            expected = self._expected_data.pop(0)
            if expected != data:
                raise AssertionError("Expected data '%s' does not match '%s'" % (expected, data))

    def close(self):
        self._expected_data = []

    def start_verifying_calvinsys(self):
        self._write_allowed = False
