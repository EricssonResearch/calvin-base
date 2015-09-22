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

import os.path
import os
from calvin.runtime.south.plugins.async import serialport
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class SerialPort(object):

    def __init__(self, devicename, baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts, trigger, actor_id):
        self.actor_id = actor_id
        self.port = serialport.SP(
            devicename,
            baudrate,
            bytesize,
            parity,
            stopbits,
            timeout,
            xonxoff,
            rtscts,
            trigger,
            actor_id)

    def write(self, data):
        self.port.write(data)

    def read(self):
        return self.port.read()

    def has_data(self):
        return self.port.hasData()

    def close(self):
        self.port.close()


class SerialPortHandler(object):

    def __init__(self, node, actor):
        self.node   = node
        self._actor = actor

    def open(self, devicename, baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts):
        if not os.path.exists(devicename):
            raise Exception("Device not found")

        return SerialPort(
            devicename,
            baudrate,
            bytesize,
            parity,
            stopbits,
            timeout,
            xonxoff,
            rtscts,
            self.node.sched.trigger_loop,
            self._actor.id)

    def close(self, port):
        port.close()


def register(node, actor):
    """
        Called when the system object is first created.
    """
    return SerialPortHandler(node, actor)
