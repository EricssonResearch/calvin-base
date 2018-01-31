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

import os
from calvin.runtime.south.calvinsys import base_calvinsys_object

class GetSize(base_calvinsys_object.BaseCalvinsysObject):
    """
    FileSize - Get size of file
    """

    init_schema = {
        "type": "object",
        "properties": {
            "basedir": {
                "description": "Base directory",
                "type": "string"
            },
            "filename": {
                "description": "Filename",
                "type": "string"
            }
        },
        "description": "Get size of file",
        "required": ["basedir", "filename"]
    }

    can_read_schema = {
        "description": "Returns True if file length can be read",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read file length"
    }

    def init(self, basedir, filename, **kwargs):
        self.filelen = None
        path = os.path.join(basedir, filename)

        if '..' in filename:
            raise Exception("'..' not allowed in filename")

        if not os.path.exists(path):
            raise Exception("File '%s' not found", path)

        self.filelen = os.path.getsize(path)

    def can_read(self):
        return self.filelen is not None

    def read(self):
        return self.filelen

    def close(self):
        pass
