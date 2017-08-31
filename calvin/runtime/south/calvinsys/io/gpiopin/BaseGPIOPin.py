
# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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

class BaseGPIOPin(base_calvinsys_object.BaseCalvinsysObject):
    """
    GPIOPin - Object handling a general-purpose input/output pin
    """

    init_schema = {
        "type": "object",
        "properties": {
            "pin": {
                "description": "Pin number",
                "type": "integer",
                "minimum": 0
            },
            "direction": {
                "description": "Direction (IN/OUT)",
                "type": "string"
            },
            "pull": {
                "description": "Enable internal pull up/down resistor (UP/DOWN)",
                "type": "string"
            },
            "edge": {
                "description": "Edge detection (RISING/FALLING/BOTH)",
                "type": "string"
            },
            "bouncetime": {
                "description": "Bouncetime in milliseconds",
                "type": "integer",
                "minimum": 0
            }
        },
        "required": ["pin", "direction"],
        "description": "Initialize pin"
    }
    
    can_write_schema = {
        "description": "Returns True if data can be written, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Set pin state, 0/1 for state low/high",
        "enum": [0, False, 1, True]
    }

    can_read_schema = {
        "description": "Returns True if data can be read, otherwise False",
        "type": "boolean"
    }

    read_schema = {
        "description": "Get pin state, 0/1 for state low/high",
        "type": "integer",
        "minimum": 0,
        "maximum": 1
    }
