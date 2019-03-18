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

from calvin.runtime.south import asynchronous
from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.common.calvinlogger import get_logger

_log = get_logger(__name__)

class UDPListener(base_calvinsys_object.BaseCalvinsysObject):
    """
    UDPListener - A UDP socket listener
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
            }
        },
        "description": "Setup a UDP socket listener",
        "required": ["host", "port"]
    }

    can_read_schema = {
        "description": "Returns True if pending data",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read data"
    }

    def _data_received(self):
        self.calvinsys._node.sched.schedule_calvinsys(self.actor.id)
        
    def init(self, host, port):
        self._listener = asynchronous.UDPServer(host, port, self._data_received)
        self._listener.start()

    def can_read(self):
        return self._listener.have_data()

    def read(self):
        return self._listener.data_get()

    def close(self):
        self._listener.stop()
