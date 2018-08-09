# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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

from calvin.runtime.south.async import server_connection
from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class TCPServer(base_calvinsys_object.BaseCalvinsysObject):
    """
    TCPServer - A TCP socket server
    """

    init_schema = {
        "type": "object",
        "properties": {
            "host": {
                "description": "Host",
                "type": "string"
            },
            "port": {
                "description": "Port",
                "type": "number"
            },
            "mode": {
                "description": "Mode (line, raw, http), default=line",
                "type": "string",
                "enum": ["line", "raw", "http"]
            },
            "delimiter": {
                "description": "Delimiter, default='\r\n'",
                "type": "string"
            },
            "max_length": {
                "description": "Max data length, default=8192",
                "type": "number"
            }
        },
        "description": "Setup a TCP socket server",
        "required": ["host", "port"]
    }

    can_read_schema = {
        "description": "Returns True if data can read",
        "type": "boolean"
    }

    read_schema = {
        "type": "object",
        "properties": {
            "handle": {
                "description": "Connection handle",
                "type": "string"
            },
            "data": {
                "description": "Received data"
            }
        },
        "description": "Read data",
        "required": ["handle", "data"]
    }

    can_write_schema = {
        "description": "Return True if data can be written",
        "type": "boolean"
    }

    write_schema = {
        "type": "object",
        "properties": {
            "handle": {
                "description": "Connection handle",
                "type": "string"
            },
            "data": {
                "description": "Data to send"
            }
        },
        "description": "Write data",
        "required": ["handle", "data"]
    }

    def init(self, host, port, mode, delimiter, max_length):
        self._server = server_connection.ServerProtocolFactory(trigger=self.calvinsys._node.sched.schedule_calvinsys,
            mode=mode,
            delimiter=delimiter,
            max_length=max_length,
            actor_id=self.actor.id)
        self._server.start(host, port)
        self._connections = {}

    def can_read(self):
        if self._server.pending_connections:
            addr, conn = self._server.accept()
            self._connections[str(addr)] = conn
        for h, c in self._connections.items():
            if c.connection_lost:
                del self._connections[h]
            if c.data_available:
                return True
        return False

    def read(self):
        for h, c in self._connections.items():
            if c.data_available:
                return {"handle": h, "data": c.data_get()}

    def can_write(self):
        if self._connections:
            return True
        return False

    def write(self, data):
        if data["handle"] in self._connections:
            self._connections[data["handle"]].send(data["data"])

    def close(self):
        try:
            self._server.stop()
        except:
            pass
