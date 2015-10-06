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

from twisted.internet.abstract import FileDescriptor
from twisted.internet import fdesc
from twisted.internet import reactor
import os
import select


class GPIOPin(FileDescriptor):
    """A Calvin sysfs based gpio pin object"""
    def __init__(self, trigger, pin, direction, delay=0.2):
        """
        Export gpio pin and set direction and read delay
        """
        super(GPIOPin, self).__init__()
        self.trigger = trigger
        self.pin = pin
        self.direction = direction
        self.delay = delay
        self.data = None
        self.last_read = None

        # export pin
        if not os.path.exists("/sys/class/gpio/gpio" + str(self.pin)):
            fp = open("/sys/class/gpio/export", "w")
            fp.write(str(self.pin))
            fp.close()

        # set direction
        fp = open("/sys/class/gpio/gpio" + str(self.pin) + "/direction", "w")
        fp.write(self.direction)
        fp.close()

        if self.direction == "out":
            self.fp = open("/sys/class/gpio/gpio" + str(self.pin) + "/value", "w")
            self.startWriting()
        elif self.direction == "in":
            self.fp = open("/sys/class/gpio/gpio" + str(self.pin) + "/value", "r")
            self.delayedCall = reactor.callLater(self.delay, self.doRead)
        else:
            raise Exception("Pin direction must be in or out")

        fdesc.setNonBlocking(self)
        self.connected = True  # Required by FileDescriptor class

    def fileno(self):
        return self.fp.fileno()

    def writeSomeData(self, data):
        return fdesc.writeToFD(self.fp.fileno(), data)

    def _closeWriteConnection(self):
        self.connected = False
        self.fp.close()
        if os.path.exists("/sys/class/gpio/gpio" + str(self.pin)):
            fp = open("/sys/class/gpio/unexport", "w")
            fp.write(str(self.pin))
            fp.close()

    def dataRead(self, data):
        self.data = data
        self.fp.seek(0)
        self.delayedCall = reactor.callLater(self.delay, self.doRead)

    def doRead(self):
        if self.direction == "in":
            self.trigger()
            return fdesc.readFromFD(self.fp.fileno(), self.dataRead)

    def set_state(self, state):
        """
        Set state of pin
        """
        if self.direction == "out":
            self.fp.write(state)
            self.fp.seek(0)
        else:
            raise Exception("Pin direction must be out")

    def has_changed(self):
        """
        True if data has changed since last call to get_state()
        """
        return self.data != self.last_read

    def get_state(self):
        """
        Get state of pin
        """
        if self.direction == "in":
            self.last_read = self.data
            return self.data
        else:
            raise Exception("Pin direction must be in")

    def close(self):
        """
        Close file and unexport pin
        """
        self.loseConnection()

