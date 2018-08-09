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


class Pipe(FileDescriptor):
    def __init__(self, pipe, notify):
        super(Pipe, self).__init__()
        self.pipe = pipe
        self.notify = notify
        self.connected = True

        self.startReading()

    def fileno(self):
        return self.pipe.fileno()

    def doRead(self):
        self.notify()

    def close(self):
        self.connected = False
        self.stopReading()
        self.pipe.close()
