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


class BaseDisplay(base_calvinsys_object.BaseCalvinsysObject):
    """
    Display messages on AdaFruit 16x2 LCD display (without back plate)
    """

    init_schema = {
        "type": "object",
        "properties": {
        },
        "description": "Send all incoming data to display "
    }

    can_write_schema = {
        "description": "True if display ready to show next message",
        "type": "boolean"
    }

    write_schema = {
        "description": "Set message to display",
        "type": ["boolean", "integer", "number", "string", "array", "object", "null"]
    }
