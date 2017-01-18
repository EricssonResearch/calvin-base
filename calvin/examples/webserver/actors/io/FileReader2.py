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
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken


def absolute_filename(filename):
    """Test helper - get absolute name of file"""
    # @TODO: Could be done better
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


class FileReader2(Actor):

    """
    Read a file line by line, and send each line as a token on output port.

    When there is no more data to be read, an EOS token is sent
    and a status_OK value is sent on the 'ses' (stream end status) port.
    If the file doesn't exist, an EOS token is sent
    and a status_ERR value is sent on the 'ses' (stream end status) port.
    The values for status_OK and status_ERR defaults to 0 and 1, respectively,
    but can be set per instance by passing the desired values as parameters.

    Inputs:
      filename : File to read. If file doesn't exist, an ExceptionToken is produced
    Outputs:
      out : Each token is a line of text, or EOSToken.
      ses : Stream End Status
    """

    @manage(['status_OK', 'status_ERR'])
    def init(self, status_OK=0, status_ERR=1):
        self.status_OK = status_OK
        self.status_ERR = status_ERR
        self.file_not_found = False
        self.file = None
        self.use('calvinsys.io.filehandler', shorthand="file")

    @stateguard(lambda self: not self.file)
    @condition(['filename'], [])
    def open_file(self, filename):
        try:
            self.file = self['file'].open(filename, "r")
        except:
            self.file = None
            self.file_not_found = True
        

    @stateguard(lambda self: self.file_not_found)
    @condition([], ['out', 'ses'])
    def file_not_found(self):
        self.file_not_found = False  # Only report once
        return (EOSToken(), self.status_ERR)

    @stateguard(lambda self: self.file and not self.file.eof() and self.file.has_data())
    @condition([], ['out'])
    def readline(self):
        line = self.file.read_line()
        return (line, )

    @stateguard(lambda self: self.file and self.file.eof())
    @condition([], ['out', 'ses'])
    def eof(self):
        self['file'].close(self.file)
        self.file = None
        return (EOSToken(), self.status_OK)

    action_priority = (readline, eof, open_file, file_not_found)
    requires = ['calvinsys.io.filehandler']

    # Assumes file contains "A\nB\nC\nD\nE\nF\nG\nH\nI"

    test_set = [
        {  # Test 3, read a non-existing file
            'in': {'filename': "no such file"},
            'out': {'out': ["End of stream"], 'ses':[1]}
        },
        {  # Test 1, read a file
            'in': {'filename': absolute_filename('data.txt')},
            'out': {'out': ['A', 'B', 'C', 'D']}
        },
        {  # Test 2, read more of file
            'out': {'out': ['E', 'F', 'G', 'H']}
        },
        {  # Test 3, read last of file
            'out': {'out': ['I', "End of stream"], 'ses':[0]}
        }

    ]
