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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *
from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.runtime.south.plugins.async import filedescriptor

class StdIn(base_calvinsys_object.BaseCalvinsysObject):
    """
    File - Read from stdin
    """

    init_schema = {
        "description": "Read from stdin"
    }

    can_read_schema = {
        "description": "Returns True if data can be read",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read data"
    }

    def init(self, **kwargs):
        self.fd = filedescriptor.FDStdIn(self.actor, self.calvinsys.scheduler_wakeup)

    def can_read(self):
        if self.fd.hasData():
            return True
        return False

    def read(self):
        return self.fd.read()

    def close(self):
        self.fd.close()
