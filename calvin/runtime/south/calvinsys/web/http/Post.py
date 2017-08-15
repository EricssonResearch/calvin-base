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

from calvin.runtime.south.plugins.async import threads
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
            }
        },
        "description": "Setup HTTP command"
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

    def init(self, url=None, data=None, cmd="POST", timeout=5.0):
        self._url = url
        self._data = data
        self._cmd = requests.put if cmd == "PUT" else requests.post
        self._in_progress = None
        self._result = None
        self._timeout = timeout

    def can_write(self):
        # No on-going request and no pending result
        return self._in_progress is None and self._result is None
    
    def _request_finished(self, request, *args, **kwargs):
        if request.status_code == requests.codes.ok:
            # Everything checks out, return it
            self._result = request.text
        else:
            # something went wrong
            _log.warning("Request failed with: {}".format(request.status_code))
            self._result = ""
        self._in_progress = None
        self.scheduler_wakeup()

    def _request_error(self, *args, **kwargs):
        _log.error("Request had errors: {} / {}".format(args, kwargs))
        self._result = ""
        self._in_progress = None
        self.scheduler_wakeup()
        
    def write(self, write_data):
        assert self._in_progress is None
        url = self._url
        data = self._data
        
        if data is None:
            data = write_data
        elif url is None:
            url = write_data
        self._in_progress = threads.defer_to_thread(self._cmd, url, data=data, timeout=self._timeout)
        self._in_progress.addCallback(self._request_finished)
        self._in_progress.addErrback(self._request_error)

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
