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

from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.north.calvin_token import ExceptionToken
from serial import PARITY_NONE, STOPBITS_ONE, EIGHTBITS

_log = get_logger(__name__)


class SerialPort(Actor):

    """
    Read/write data from serial port.

    inputs:
      in  : Tokens to write.
    Outputs:
      out : Tokens read.
    """

    @manage(['devicename', 'baudrate', 'bytesize', 'parity', 'stopbits', 'timeout', 'xonxoff', 'rtscts'])
    def init(self, devicename, baudrate, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE, timeout=0, xonxoff=0, rtscts=0):
        self.not_found = False
        self.devicename = devicename
        self.baudrate = baudrate
        try:
            self.device = self.calvinsys.io.serialport.open(
                devicename,
                baudrate,
                bytesize,
                parity,
                stopbits,
                timeout,
                xonxoff,
                rtscts)
        except:
            self.device = None
            self.not_found = True

    @stateguard(lambda self: self.not_found)
    @condition([], ['out'])
    def device_not_found(self):
        token = ExceptionToken(value="Device not found")
        self.not_found = False  # Only report once
        return (token, )

    @stateguard(lambda self: self.device and self.device.has_data())
    @condition([], ['out'])
    def read(self):
        data = self.device.read()
        return (data, )

    @stateguard(lambda self: self.device)
    @condition(action_input=['in'])
    def write(self, data):
        self.device.write(str(data))

    action_priority = (device_not_found, read, write)
