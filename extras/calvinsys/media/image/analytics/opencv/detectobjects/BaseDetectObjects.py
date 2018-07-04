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


from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *
from calvin.runtime.south.calvinsys import base_calvinsys_object

 
class BaseDetectObjects(base_calvinsys_object.BaseCalvinsysObject):
    """
    DetectObjects: Find (and optionally mark) preconfigured objects in image
    """

    init_schema = {
        "description": "Setup DetectObjetcs",
        "type": "object",
        "properties": {
            "mark_objects": {
                "description": "Mark found objects in image",
                "type": "boolean"
            }
        }
    }
    
    can_write_schema = {
        "description": "True iff module is ready for next image"
    }
    
    write_schema = {
        "description": "Count objects as defined by haarcascade file. Input b64 encoded image",
        "type": "string"
    }
    
    can_read_schema = {
        "description": "True iff prevoius image has finished processing"
    }
    
    read_schema = {
        "description": "Mark objects as defined by haarcascade file. Input b64 encoded image, return b64 encoded image with found objects marked",
        "type": ["string", "integer"]
    }
