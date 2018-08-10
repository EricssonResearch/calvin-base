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
import sensehat
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class SenseHatDisplay(base_calvinsys_object.BaseCalvinsysObject):
    """
    Display text on SenseHat matrix on Raspberry Pi
    """

    init_schema = {
        "type": "object",
        "properties": {
            "prefix": {
                "description": "String to prefix all data",
                "type": "string"
            },
            "rotation": {
                "description": "Rotation of display",
                "type": "integer",
                "enum": [0, 90, 180, 270]
            },
            "textcolor": {
                "description": "Color of text as list of RGB values",
                "type": "array",
                "items": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "exclusiveMaximum": False
                },
                "minItems": 3,
                "maxItems": 3
            },
            "backgroundcolor": {
                "description": "Color of background as list of RGB values",
                "type": "array",
                "items": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "exclusiveMaximum": False
                },
                "minItems": 3,
                "maxItems": 3
            }
        },
        "description": "Display incoming text on SenseHat LED Matrix"
    }

    can_write_schema = {
        "description": "Ready for next message",
        "type": "boolean"
    }

    write_schema = {
        "description": "Write data to standard out",
        "type": ["boolean", "integer", "number", "string", "array", "object", "null"]
    }

    def init(self, prefix=None, rotation=0, textcolor=(255,255,255), backgroundcolor=(0,0,0), **kwargs):
        self._prefix = prefix
        self._can_write = True
        self._sensehat = sensehat.SenseHat(rotation=rotation, textcolor=textcolor, backgroundcolor=backgroundcolor)

    def can_write(self):
        return self._can_write

    def write(self, data=None):
        def done(*args, **kwargs):
            self._can_write = True
            self.scheduler_wakeup()

        self._can_write = False
        msg = ""
        if data and self._prefix:
            msg = "{}: {}".format(self._prefix, data)
        elif data:
            msg = "{}".format(data)
            pass
        elif self._prefix:
            msg = "{}".format(self._prefix)
        self._sensehat.show_message(msg, done)

    def close(self):
        pass

