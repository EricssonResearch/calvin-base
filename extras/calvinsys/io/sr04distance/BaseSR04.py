
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

class BaseSR04(base_calvinsys_object.BaseCalvinsysObject):
    """
    Measuring distance
    """
    init_schema = {
        "type": "object",
        "properties": {
            "echo_pin": {
                "description": "Pin to use for echo detection",
                "type": "integer",
                "minimum": 1
            },
            "trigger_pin":{
                "description": "Pin to use to trigger measurement",
                "type": "integer",
                "minimum": 1
            }
        },
        "required": ["echo_pin", "trigger_pin"],
        "description": "Initialize SR04 ultrasound distance measurement"
    }
    
    can_write_schema = {
        "description": "True iff SR04 is setup and configured",
    }

    write_schema = {
        "description": "Execute measurement",
        "type": "boolean"
    }

    can_read_schema =  {
        "description": "True iff a measurement has finished",
        "type": "boolean"
    }
    
    read_schema = {
        "description": "Latest measurement (in mm)",
        "type": "number"
    }

