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

# Note, the wsbroadcast plugin has twisted dependency
from calvin.runtime.south.plugins.web.twistedimpl import wsbroadcast
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)


class Broadcast(base_calvinsys_object.BaseCalvinsysObject):
    """
    Broadcast - Broadcast messages to any client connected
    """

    init_schema = {
        "description": "Setup server and wait for a connection",
        "properties": {
            "host":  {
                "description": "ip address to the websocket server",
                "type": "string"
            },
            "port": {
                "description": "port of the websocket server",
                "type": "number"
            }
        },
        "required": ["host", "port"],
    }

    can_write_schema = {
        "description": "Returns True if data can be posted, i.e any client connected, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Broadcasts token to the connected clients",
    }

    def init(self, host, port):
        try:
            self._server = wsbroadcast.MyBroadcastServer(host, port)
        except Exception as e:
            self._server = None
            _log.error("Could not create websocket: {}".format(e))
            return

    def can_write(self):
        return self._server is not None

    def write(self, data):
        try:
            self._server.broadcast(data)
        except Exception as e:
            _log.error("Could not write to websocket: {}".format(e))

    def close(self):
        del self._server
        self._server = None

    def serialize(self):
        self._server.stop()
