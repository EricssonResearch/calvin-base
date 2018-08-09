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

import os.path
import os

from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.runtime.south.async import filedescriptor

_log = get_logger(__name__)

def access_allowed(filename):
    return os.access(os.path.dirname(os.path.realpath(filename)), os.W_OK | os.X_OK)

class Descriptor(base_calvinsys_object.BaseCalvinsysObject):
    """
    File - Read and write from and to a file
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
            },
            "mode": {
                "description": "Mode (r, w)",
                "type": "string"
            }
        },
        "description": "Read and write from and to a file",
        "required": ["basedir", "filename", "mode"]
    }

    can_write_schema = {
        "description": "Returns True if data can be written",
        "type": "boolean"
    }

    write_schema = {
        "description": "Write data"
    }

    can_read_schema = {
        "description": "Returns True if data can be read",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read data"
    }

    def init(self, basedir, filename, mode, **kwargs):
        path = os.path.join(basedir, filename)

        if '..' in filename:
            raise Exception("'..' not allowed in filename")

        if 'r' in mode and not os.path.exists(path):
            raise Exception("File not found")

        if 'w' in mode and not access_allowed(path):
            raise Exception("Cannot create file")

        self.fd = filedescriptor.FD(self.actor, self.calvinsys.scheduler_wakeup, path, mode)
        self.mode = mode

    def can_write(self):
        if "w" in self.mode:
            return True
        return False

    def write(self, data=None):
        self.fd.write(data)

    def can_read(self):
        if "r" in self.mode and self.fd.hasData():
            return True
        return False

    def read(self):
        return self.fd.read()

    def close(self):
        self.fd.close()
