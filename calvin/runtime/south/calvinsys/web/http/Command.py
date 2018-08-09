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

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class Command(base_calvinsys_object.BaseCalvinsysObject):
    """
    Command - Execute HTTP Command, returning result
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
                "type": ["string", "null"]
            },
            "cmd": {
                "description": "Command - PUT or POST, default POST",
                "type": "string",
                "enum": ["PUT", "POST", "DELETE", "GET"]
            },
            "timeout": {
                "description": "Timeout (in seconds) for command. Default 5 seconds)",
                "type" : "number"
            },
            "nodata": {
                "description": "Not interested in result of operation (no need for read to ack)",
                "type": "boolean"
            },
            "onlydata": {
                "description": "Only return body of operation, converted to given type",
                "enum": ["integer", "number", "string"]
            },
            "headers": {
                "description": "additional headers to include in request",
                "type": ["object", "null"]
            },
            "params": {
                "description": "additional parameters to pass in query string",
                "type": ["object", "null"]
            },
            "auth": {
                "description": "username & password (optional) to use",
                "type": ["object", "null"],
                "properties": {
                    "authtype": {
                        "enum": ["basic", "digest"]
                    },
                    "username": {
                        "type": "string"
                    },
                    "password": {
                        "type": "string"
                    }
                },
                "required": ["authtype", "username"]
            }
        },
        "description": "Setup HTTP command",
        "required": ["cmd"]
    }

    can_write_schema = {
        "description": "Returns True if HTTP command is ready to be executed",
        "type": "boolean"
    }

    write_schema = {
        "description": "Send data (or nothing) to URL; boolean accepted as trigger, but will not be sent. If dictionary then url, data, params, headers taken from it ",
        "type": ["string", "null", "boolean", "object"],
        "properties": {
            "url": {
                "type": "string"
            },
            "params": {
                "type": ["object", "null"]
            },
            "headers": {
                "type": ["object", "null"]
            },
            "data": {
                "type": ["string", "null"]
            },
            "auth": {
                "type": ["object", "null"],
                "properties": {
                    "authtype": {
                        "enum": ["digest", "basic"]
                    },
                    "username": {
                        "type": "string"
                    },
                    "password": {
                        "type": "string"
                    }
                }
            }
        },
    }

    can_read_schema = {
        "description": "Returns True iff request has finished and data can be read",
        "type": "boolean"
    }

    read_schema = {
        "description": "Get result from request; default dictionary with headers, body, and status, otherwise of type as given in onlydata",
        "type" : ["object", "number", "integer", "string"],
        "properties": {
            "body": {
                "type": "string"
            },
            "headers": {
                "type": "object"
            },
            "status": {
                "type": "integer"
            }
        }
    }


    @staticmethod
    def get_auth_method(auth):
        if auth.get("authtype") == "basic":
            auth = HTTPBasicAuth(auth.get("username"), auth.get("password"))
        elif auth.get("authtype") == "digest":
            auth = HTTPDigestAuth(auth.get("username"), auth.get("password"))
        else:
            _log.warning("Ignoring unknown authentication method {}".format(auth.get("authtype")))
            auth = None

        return auth

    def init(self, cmd, url=None, data=None, timeout=5.0, auth=None, headers=None, params=None, onlydata=None, nodata=False):
        if auth:
            auth = Command.get_auth_method(auth)

        self.settings = {
            "headers": headers or {},
            "params": params or {},
            "auth": auth,
            "timeout": timeout,
            "nodata": nodata,
            "onlydata": onlydata
        }
        self.command = {"POST": requests.post, "PUT": requests.put, "DELETE": requests.delete, "GET": requests.get}.get(cmd, None)
        self.url = url
        self.data = data

        self.result = None
        self.busy = False

    def can_write(self):
        return not self.busy and not self.result

    def write(self, data=None):
        def error(err):
            _log.warning("Request had errors: {}".format(err))

        def success(response):
            if self.settings.get("nodata"):
                #do nothing
                pass
            elif self.settings.get("onlydata"):
                # convert body to given type, return only body
                dtype = self.settings.get("onlydata")
                try:
                    self.result = {"integer": int, "number": float, "string": lambda x: x}.get(dtype)(response.text)
                except Exception:
                    _log.warning("Failed to convert {} to {}".format(response.text, dtype))
            else:
                # return everything
                # Headers are case-insensitive, so we downcase everything
                headers = { k.lower():v for k, v in dict(response.headers).items()}
                self.result = {"body": response.text, "status": response.status_code, "headers": headers }

        def done(*args, **kwargs):
            self.scheduler_wakeup()

        http_data = None
        if not data or isinstance(data, bool):
            http_data = self.data

        url = self.url
        headers = self.settings.get("headers")
        params = self.settings.get("params")
        auth = self.settings.get("auth")

        if isinstance(data, dict):
            # User supplied headers, params, url
            if not headers:
                headers = data.get("headers", {})
            if not params:
                params = data.get("params", {})
            if not auth:
                auth = data.get("auth", None)
                if auth:
                    auth = Command.get_auth_method(auth)
            if not url:
                url = data.get("url")
            if data.get("data"):
                http_data = data.get("data")

        defer = threads.defer_to_thread(self.command, url=url, data=http_data,
                                        timeout=self.settings.get("timeout"), headers=headers,
                                        params=params, auth=auth)
        defer.addCallback(success)
        defer.addErrback(error)
        defer.addBoth(done)

    def can_read(self):
        return not self.busy and self.result is not None


    def read(self):
        result = self.result
        self.result = None
        return result

    def close(self):
        pass
