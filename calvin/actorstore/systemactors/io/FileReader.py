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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
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
        self.did_read = False
        self.file_not_found = False
        self.file = None
        self.use(requirement='calvinsys.io.filehandler', shorthand='file')

    @condition(['filename'], [])
    @guard(lambda self, filename: not self.file)
    def open_file(self, filename):
        try:
            self.file = self['file'].open(filename, "r")
        except:
            self.file = None
            self.file_not_found = True
        return ActionResult()

    @condition([], ['out'])
    @guard(lambda self: self.file_not_found)
    def file_not_found(self):
        token = ExceptionToken(value="File not found")
        self.file_not_found = False  # Only report once
        return ActionResult(production=(token, ))

    @condition([], ['out'])
    @guard(lambda self: self.file and self.file.has_data())
    def readline(self):
        line = self.file.read_line()
        return ActionResult(production=(line, ))

    @condition([], ['out'])
    @guard(lambda self: self.file and self.file.eof())
    def eof(self):
        self['file'].close(self.file)
        self.file = None
        return ActionResult(production=(EOSToken(), ))

    action_priority = (open_file, file_not_found, readline, eof)
    requires =  ['calvinsys.io.filehandler']

    # Assumes file contains "A\nB\nC\nD\nE\nF\nG\nH\nI"

    test_set = [
        {  # Test 3, read a non-existing file
            'in': {'filename': "no such file"},
            'out': {'out': ["File not found"]}
        },
        {  # Test 1, read a file
            'in': {'filename': absolute_filename('data.txt')},
            'out': {'out': ['A', 'B', 'C', 'D']}
        },
        {  # Test 2, read more of file
            'out': {'out': ['E', 'F', 'G', 'H']}
        },
        {  # Test 3, read last of file
            'out': {'out': ['I']}
        }

    ]
