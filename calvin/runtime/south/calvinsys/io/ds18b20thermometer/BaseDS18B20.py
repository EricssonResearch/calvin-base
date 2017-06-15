
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

class BaseDS18B20(base_calvinsys_object.BaseCalvinsysObject):
    """
    Measuring temperature
    """
    init_schema = {
        "description": "Initialize DS18B20 thermometer",
        "type": "object",
        "properties": {
            "id":  {
                "type": "string"
            }
        }
    }
    
    can_write_schema = {
        "description": "True iff DS18B20 is setup and configured",
        "type": "boolean"
    }

    write_schema = {
        "description": "Read temperature",
        "type": "boolean",
    }

    can_read_schema =  {
        "description": "True iff a reading has finished",
        "type": "boolean"
    }
    
    read_schema = {
        "description": "Latest reading (in degrees C)",
        "type": "number"
    }

