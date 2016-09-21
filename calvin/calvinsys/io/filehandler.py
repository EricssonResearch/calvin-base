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

from calvin.runtime.south.plugins.async import filedescriptor

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class File(object):
    def __init__(self, node, fname, mode):
        self.fd = filedescriptor.FD(node.sched.trigger_loop, fname, mode)

    def write(self, data):
        self.fd.write(data)

    def write_line(self, data):
        self.fd.writeLine(data)

    def has_data(self):
        return self.fd.hasData()

    def eof(self):
        return self.fd.endOfFile()

    def read_line(self):
        return self.fd.readLine()

    def close(self):
        self.fd.close()

    def read(self):
        return self.fd.read()


class StdIn(File):
    def __init__(self, node):
        self.fd = filedescriptor.FDStdIn(node.sched.trigger_loop)


def access_allowed(filename):
    return os.access(os.path.dirname(os.path.realpath(filename)), os.W_OK | os.X_OK)


class FileHandler(object):
    def __init__(self, node):
        super(FileHandler, self).__init__()
        self.node = node

    def open(self, fname, mode):
        if 'r' in mode and not os.path.exists(fname):
            raise Exception("File not found")

        if 'w' in mode and not access_allowed(fname):
            raise Exception("Cannot create file")

        return File(self.node, fname, mode)

    def open_stdin(self):
        return StdIn(self.node)

    def close(self, fp):
        fp.close()


def register(node, actor, io=None):
    """
        Called when the system object is first created.
    """
    return FileHandler(node)
