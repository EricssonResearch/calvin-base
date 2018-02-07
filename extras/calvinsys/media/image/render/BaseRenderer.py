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

    
class BaseRenderer(base_calvinsys_object.BaseCalvinsysObject):
    """
    Renderer - Render given (base64 encoded) image in some way
    """

    init_schema = {
        "type": "object",
        "description": "Set up renderer"
    }
    
    can_write_schema = {
        "description": "True it is possible to render a new image",
        "type": "boolean"
    }

    write_schema = {
        "description": "Set next image to render",
        "type": "string"
    }
