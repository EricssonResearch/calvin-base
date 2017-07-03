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
        "description": "Any data"
    }

    def init(self, **kwargs):
        pass

    def can_write(self):
        return True

    def write(self, data):
        print data

    def close(self):
        pass
