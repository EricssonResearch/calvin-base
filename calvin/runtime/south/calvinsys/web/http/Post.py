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

import requests

from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class Post(base_calvinsys_object.BaseCalvinsysObject):
    """
    Post - HTTP Post (or Put) data to given address and return result
    """

    init_schema = {
        "type": "object",
        "properties": {
            "url": {
                "description": "HTTP address",
                "type": "string"
            },
            "data": {
                "description": "data to send",
                "type": "string"
            },
            "cmd": {
                "description": "Command - PUT or POST, default POST",
                "type": "string",
                "enum": ["PUT", "POST"]
            },
            "timeout": {
                "description": "Timeout (in seconds) for command. Default 5 seconds)",
                "type" : "number"
            },
            "nodata": {
                "description": "Not interested in result of operation (no read)",
                "type": "boolean"
            },
            "headers": {
                "description": "additional headers to include in request",
                "type": "object"
            }
        },
        "description": "Setup HTTP command",
        "required": ["url", "cmd"]
    }

    can_write_schema = {
        "description": "Returns True if HTTP command is ready to be executed",
        "type": "boolean"
    }

    write_schema = {
        "description": "Send data to URL",
        "type": ["string", "null"]
    }

    can_read_schema = {
        "description": "Returns True iff request has finished",
        "type": "boolean"
    }

    read_schema = {
        "description": "Get result from request, always a string (no binary)",
        "type" : "string"
    }

    def init(self, url, cmd="POST", data=None, nodata=False, timeout=5.0, headers=None):
        self._headers = headers or {}
        self._nodata = nodata
        self._url = url
        self._data = data
        self._cmd = requests.put if cmd == "PUT" else requests.post
        self._in_progress = None
        self._result = None
        self._timeout = timeout

    def can_write(self):
        if self._nodata:
            return self._in_progress is None
        else:
            # No on-going request and no pending result
            return self._in_progress is None and self._result is None

    def write(self, write_data):

        def finished(request):
            request.raise_for_status()
            self._result = request.text

        def error(*args, **kwargs):
            _log.error("Request had errors: {} / {}".format(args, kwargs))
            self._result = ""

        def reset(*args, **kwargs):
            self._in_progress = None
            self.scheduler_wakeup()

        assert self._in_progress is None
        url = self._url
        data = self._data

        if data is None:
            data = write_data
        elif url is None:
            url = write_data
        self._in_progress = threads.defer_to_thread(self._cmd, url, data=data, timeout=self._timeout, headers=self._headers)
        self._in_progress.addCallback(finished)
        self._in_progress.addErrback(error)
        self._in_progress.addBoth(reset)

    def can_read(self):
        return self._result is not None

    def read(self):
        assert self._result is not None
        result = self._result
        self._result = None
        return result

    def close(self):
        if self._in_progress:
            self._in_progress.cancel()
        pass
