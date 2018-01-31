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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken


def absolute_filename(filename):
    """Test helper - get absolute name of file
    @TODO: Possibly not the best way of doing this
    """
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


class FileReader(Actor):

    """
    Read a file line by line, and send each line as a token on output port

    Inputs:
      filename : File to read. If file doesn't exist, an ExceptionToken is produced
    Outputs:
      out : Each token is a line of text, or EOSToken.
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self.file_not_found = False
        self.file = None
        self.filelen = 0
        self.totalread = 0

    def did_migrate(self):
        self.setup()

    def will_end(self):
        if self.file is not None:
            calvinsys.close(self.file)
            self.file = None

    @stateguard(lambda self: not self.file)
    @condition(['filename'], [])
    def open_file(self, filename):
        obj = calvinsys.open(self, "io.filesize", filename=filename)
        if calvinsys.can_read(obj):
            self.filelen = calvinsys.read(obj)
            calvinsys.close(obj)
            self.file = calvinsys.open(self, "io.filereader", filename=filename)
        if self.file is None:
            self.file_not_found = True

    @stateguard(lambda self: self.file_not_found)
    @condition([], ['out'])
    def file_not_found(self):
        token = ExceptionToken(value="File not found")
        self.file_not_found = False  # Only report once
        return (token, )

    @stateguard(lambda self: self.file is not None and calvinsys.can_read(self.file))
    @condition([], ['out'])
    def read(self):
        data = calvinsys.read(self.file)
        self.totalread += len(data)
        return (data, )

    @stateguard(lambda self: self.file is not None and self.totalread == self.filelen)
    @condition([], ['out'])
    def eof(self):
        calvinsys.close(self.file)
        self.file = None
        self.filelen = 0
        self.totalread = 0
        return (EOSToken(), )

    action_priority = (open_file, file_not_found, read, eof)
    requires = ['io.filereader', 'io.filesize']

    test_calvinsys = {
        'io.filereader': {'read': ['the quick brown fox jumped over the lazy dog']},
        'io.filesize': {'read': [44]}
    }
    test_set = [
        {
            'inports': {'filename': ['data.txt']},
            'outports': {'out': ['the quick brown fox jumped over the lazy dog']},
        }
    ]
