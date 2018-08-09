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

from calvin.runtime.south.async import client_connection
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class SocketClient(base_calvinsys_object.BaseCalvinsysObject):
    """
    SocketClient - A TCP/UDP socket client
    """

    init_schema = {
        "type": "object",
        "properties": {
            "address": {
                "description": "Address",
                "type": "string"
            },
            "port": {
                "description": "Port",
                "type": "number"
            },
            "connection_type": {
                "description": "Connection type - TCP or UDP",
                "type": "string",
                "enum": ["TCP", "UDP"]
            },
            "mode": {
                "description": "Mode",
                "type": "string",
                "enum": ["raw", "string", "delimiter"]
            },
            "delimitier": {
                "description": "Delimiter",
                "type": "string"
            }
        },
        "description": "Setup TCP/UDP socket connection",
        "required": ["address", "port", "connection_type"]
    }

    can_write_schema = {
        "description": "Returns True if data can be sent",
        "type": "boolean"
    }

    write_schema = {
        "description": "Send data"
    }

    can_read_schema = {
        "description": "Returns True if data can be read",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read data"
    }

    def init(self, address, port, connection_type, mode="raw", delimiter="\r\n"):
        self.connection = None
        self.data = b""
        if connection_type == "TCP":
            connection_factory = client_connection.TCPClientProtocolFactory(mode=mode, delimiter=delimiter,
                server_node_name=None,
                callbacks={'data_received':[CalvinCB(self._data_received)]})
        elif connection_type == "UDP":
            connection_factory = client_connection.UDPClientProtocolFactory(callbacks={'data_received': [CalvinCB(self._data_received)]})

        connection_factory.callback_register('connected', CalvinCB(self._connected, connection_factory))
        connection_factory.callback_register('disconnected', CalvinCB(self._disconnected))
        connection_factory.callback_register('connection_failed', CalvinCB(self._connection_failed, connection_factory))
        connection_factory.connect(address, port)

    def _disconnected(self, addr, reason):
        self.connection = None

    def _connected(self, connection_factory, addr):
        self.connection = connection_factory

    def _connection_failed(self, connection_factory, addr, reason):
        self.connection = None

    def _data_received(self, data):
        self.data += data
        self.scheduler_wakeup()

    def can_write(self):
        if self.connection:
            return True
        return False

    def write(self, data):
        if self.connection:
            self.connection.send(data)

    def can_read(self):
        if len(self.data) > 0:
            return True
        return False

    def read(self):
        data = self.data
        self.data = b""
        return data

    def close(self):
        try:
            if self.connection:
                self.connection.disconnect()
                self.connection = None
        except:
            pass
