
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

class BaseKY040(base_calvinsys_object.BaseCalvinsysObject):
    """
    A knob for inputs
    """
    init_schema = {
        "description": "Initialize KY-040 rotary encoder",
        "type": "object",
        "properties": {
            "switch_pin":  {
                "type": "integer"
            },
            "clock_pin": {
                "type": "integer"
            },
            "data_pin": {
                "type": "integer"
            }
        }
    }
    
    can_write_schema = {
        "description": "True iff rotary encoder is setup and configured",
        "type": "boolean"
    }

    write_schema = {
        "description": "Start/stop listening to knob or switch",
        "type": "boolean",
    }

    can_read_schema =  {
        "description": "True iff there is a value to read",
        "type": "boolean"
    }
    
    read_schema = {
        "description": "Fetch a value - True/False for switch, -1, 1 for knob",
        "type": [ "integer", "boolean" ]
    }

