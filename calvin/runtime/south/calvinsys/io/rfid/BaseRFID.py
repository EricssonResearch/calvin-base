# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

class BaseRFID(base_calvinsys_object.BaseCalvinsysObject):
    """
    Driver for RFID readers
    TODO: RFID writers 
    """
    init_schema = {
        "description": "Read data from RFID devices",
        "type": "object",
        "properties": {
            "irq_pin": {
                "description": "Pin number for IRQ signal",
                "type": "integer",
                "minimum": 0
            }, 
            "spi_device": {
                "description": "SPI device number",
                "type": "integer",
                "minimum": 0,
                "maximum": 1
            }
        }
    }
    
    can_read_schema =  {
        "description": "True iff a reading has finished",
        "type": "boolean"
    }
    
    read_schema = {
        "description": "RFID data",
        "type": "object"
    }
