
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

class BasePWM(base_calvinsys_object.BaseCalvinsysObject):
    """
    PWM - Handling PWM of gpio pin
    """

    init_schema = {
        "type": "object",
        "properties": {
            "pin": {
                "description": "Pin number",
                "type": "integer",
                "minimum": 0
            },
            "dutycycle": {
                "description": "PWM dutycycle (0 - 100)",
                "type" : "integer",
                "minimum": 0,
                "maximum": 100
            },
            "frequency": {
                "description": "PWM frequency, > 0 Hz ()",
                "type": "number",
                "minimum": 0.0
            }
        },
        "required": ["pin", "frequency", "dutycycle"],
        "description": "Initialize PWM for given pin"
    }
    
    can_write_schema = {
        "description": "True iff PWM is setup",
    }

    write_schema = {
        "description": "Change dutycycle of PWM",
        "type": "integer",
        "minimum": 0,
        "maximum": 100
    }


