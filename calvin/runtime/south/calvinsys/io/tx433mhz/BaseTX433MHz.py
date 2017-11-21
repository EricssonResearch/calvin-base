
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

class BaseTX433MHz(base_calvinsys_object.BaseCalvinsysObject):
    """
    Driver for 433MHz transmitters
    """
    init_schema = {
        "description": "Send data using 433MHz transmitters",
        "type": "object",
        "properties": {
            "pin": {
                "description": "Pin number",
                "type": "integer",
                "minimum": 0
            }, 
            "repeat": {
                "description": "Number of repetitions",
                "type": "integer",
                "minimum": 1
            }
        }
    }
    
    can_write_schema = {
        "description": "True if transmitter is configured",
        "type": "boolean"
    }

    write_schema = {
        "description": "Waveform array [0/1, delay in us, 0/1, delay in us, ...]",
        "type": "array"
    }

