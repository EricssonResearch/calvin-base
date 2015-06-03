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
import os


class FD(FileDescriptor):
    """A Calvin file object"""
    def __init__(self, trigger, fname, mode):
        super(FD, self).__init__()
        self.trigger = trigger
        self.fp = open(fname, mode, buffering=2048)
        fdesc.setNonBlocking(self)
        self.connected = True  # Required by FileDescriptor class
        self.data = b""

        if "w" in mode:
            self.startWriting()

        if "r" in mode:
            # In order to determine when we have reached EOF
            self.filelen = os.path.getsize(fname)
            self.totalread = 0
            self.startReading()

    def fileno(self):
        return self.fp.fileno()

    def writeSomeData(self, data):
        return fdesc.writeToFD(self.fp.fileno(), data)

    def _closeWriteConnection(self):
        self.connected = False
        self.fp.close()

    def writeLine(self, data):
        self.write(data + "\n")

    def dataRead(self, data):
        self.totalread += len(data)
        self.data += data

    def doRead(self):
        self.trigger()
        return fdesc.readFromFD(self.fp.fileno(), self.dataRead)

    def hasData(self):
        return len(self.data)

    def endOfFile(self):
        """No buffered data, and we have read the entire file, EOF"""
        return len(self.data) == 0 and self.totalread == self.filelen

    def readLine(self):
        """Return the first line of the buffer"""
        line, _, self.data = self.data.partition("\n")
        return line

    def close(self):
        self.loseConnection()

    def read(self):
        """Get buffered data"""
        data = self.data
        self.data = b""
        return data
