
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

class BaseServo(base_calvinsys_object.BaseCalvinsysObject):
    """
    Servo - Basic control of servo motor
    """

    init_schema = {
        "type": "object",
        "properties": {
            "frequency": {
                "type": "integer",
                "minimum": 0
            },
            "minimum_pulse": {
                "description": "duration of 0 degree pulse (in microseconds)",
                "type": "integer",
                "minimum": 0
            },
            "maximum_pulse": {
                "description": "duration of 180 degree pulse (in microseconds)",
                "type": "integer",
                "minimum": 0
                
            },
            "angle": {
                "description": "specify servo position using angle rather than pulsewidth",
                "type": "boolean",
                "default": True
            }
        },
        "description": "Initialize servo motor",
        "required": ["frequency", "minimum_pulse", "maximum_pulse"]
    }
    
    can_write_schema = {
        "description": "True iff servo is setup and can be controlled",
    }

    write_schema = {
        "description": "Set angle of Servo",
        "type": "number",
        "minimum": 0,
        "maximum": 180
    }


