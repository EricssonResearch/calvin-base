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

from twisted.internet.serialport import SerialPort
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet import fdesc


class RawProtocol(Protocol):

    def __init__(self, sp):
        self.data = b""
        self.sp = sp

    def dataReceived(self, data):
        self.data += data
        self.sp.trigger()


class SP(object):

    """A Calvin serialport object"""

    def __init__(self, devicename, baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts, trigger, actor_id):
        self._trigger  = trigger
        self._actor_id = actor_id
        self._port      = SerialPort(
            RawProtocol(self),
            devicename,
            reactor,
            baudrate,
            bytesize,
            parity,
            stopbits,
            timeout,
            xonxoff,
            rtscts)

    def trigger(self):
        self._trigger(actor_ids=[self._actor_id])

    def write(self, data):
        fdesc.writeToFD(self._port.fileno(), data)

    def read(self):
        data = self._port.protocol.data
        self._port.protocol.data = b""
        return data

    def hasData(self):
        return len(self._port.protocol.data)

    def close(self):
        self._port.loseConnection()
