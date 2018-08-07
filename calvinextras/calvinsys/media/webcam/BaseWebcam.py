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

class BaseWebcam(base_calvinsys_object.BaseCalvinsysObject):
    """
    Get images from webcam
    """

    init_schema = {
        "type": "object",
        "properties": {
            "height": {
                "description": "Height of image in pixels",
                "type": "integer",
                "minimum": 1,
                "maximum": 1080
            },
            "width": {
                "description": "Width of image in pixels",
                "type": "integer",
                "minimum": 1,
                "maximum": 1920
                
            }
        },
        "required": ["width", "height"],
        "description": "Set up webcam"
    }
    
    can_write_schema = {
        "description": "True if device is ready for new image request",
        "type": "boolean"
    }

    write_schema = {
        "description": "Request new image",
        "type": ["null", "boolean", "string"]
    }
    
    can_read_schema = {
        "description": "True if new image is available for reading",
        "type": "boolean"
    }
    read_schema = {
        "description": "Read image from camera as base64 encoded image",
        "type": "string"
    }
