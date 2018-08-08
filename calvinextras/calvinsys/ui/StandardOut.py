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

import calvin.runtime.south.calvinsys.ui.uicalvinsys as ui
from calvin.runtime.south.calvinsys import base_calvinsys_object


class StandardOut(base_calvinsys_object.BaseCalvinsysObject):
    """
    StandardOut - Virtual console device.
    """

    init_schema = {
        "type": "object",
        "properties": {
            "ui_def": {
                "description": "Visual appearance",
                "type": "object",
            },
            "prefix": {
                "description": "String to prefix all data",
                "type": "string"
            }
        },
        "description": "Send all incoming data to terminal (usually not very useful)"
    }

    can_write_schema = {
        "description": "Always true",
        "type": "boolean"
    }

    write_schema = {
        "description": "Write data to standard out",
        "type": ["boolean", "integer", "number", "string", "array", "object", "null"]
    }

    def init(self, ui_def=None, prefix=None, **kwargs):
        self._prefix = prefix
        ui.register_actuator(self.actor, ui_def)

    def can_write(self):
        return True

    def write(self, data=None):
        msg = ""
        if data and self._prefix:
            msg = "{}: {}".format(self._prefix, data)
        elif data:
            msg = "{}".format(data)
        elif self._prefix:
            msg = "{}".format(self._prefix)
        ui.update_ui(self.actor, msg)

    def close(self):
        pass
