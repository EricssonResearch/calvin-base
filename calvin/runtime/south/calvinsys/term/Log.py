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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class Log(base_calvinsys_object.BaseCalvinsysObject):
    """
    Basic logging to system log 
    """

    init_schema = {
        "type": "object",
        "properties": {
            "level": {
                "description": "Log level",
                "type": "string",
                "enum": ["debug", "info", "warning", "error"]
            },
            "title": {
                "description": "Eye-catch for the log entry",
                "type": "string"
            }
        },
        "required": ["level"],
        "description": "Log incoming data to system log"
    }

    can_write_schema = {
        "description": "Always true",
        "type": "boolean"
    }

    write_schema = {
        "description": "Write data to log with set log level",
        "type": ["boolean", "integer", "number", "string", "array", "object"]
    }

    def init(self, level=None, title=None, **kwargs):
        loggers = {
            "info" : _log.info,
            "debug": _log.debug,
            "warning": _log.warning,
            "error": _log.error
        }
        self._log = loggers.get(level, _log.info)
        self._title = title or ""

    def can_write(self):
        return True

    def write(self, data):
        if self._title:
            msg = "{} {}".format(self._title, data)
        else :
            msg = data
        self._log("{}".format(msg))

    def close(self):
        pass
