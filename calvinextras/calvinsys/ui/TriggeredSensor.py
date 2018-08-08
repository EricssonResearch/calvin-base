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


class TriggeredSensor(base_calvinsys_object.BaseCalvinsysObject):
    """
    Sensor - Virtual sensor device.
    """

    init_schema = {
        "type": "object",
        "properties": {
            "ui_def": {
                "description": "Visual appearance",
                "type": "object",
            }
        },
        "description": "Initialize virtual device"
    }

    can_read_schema = {
        "description": "Returns True if data can be read, otherwise False",
        "type": "boolean"
    }

    read_schema = {
        "description": "Get state",
    }

    can_write_schema = {
        "description": "Returns True if data can be written, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Set output state",
    }

    def init(self, ui_def=None, **kwargs):
        self.value = None
        ui.register_sensor(self.actor, None, ui_def)

    def can_read(self):
        return self.value is not None

    def read(self):
        value = self.value
        self.value = None
        return value

    def can_write(self):
        return True

    def write(self, value):
        # Start conversion => get current readout
        self.value = ui.sensor_state(self.actor)

    def close(self):
        # FIXME: Handle close
        pass
