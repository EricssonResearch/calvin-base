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

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


def new_filename(base, counter, suffix):
    return "%s%05d.%s" % (base, counter, suffix)
file_data = ['this is line 1', 'this is line 2']


def absolute_basename(base):
    """Test helper - get absolute name of file
        @TODO: Not a good way of doing this.
    """
    import os.path
    return os.path.join(os.path.dirname(__file__), base)


def verify_file(actor):
    import os.path
    fname = new_filename(actor.basename, actor.counter - 1, actor.suffix)
    result = os.path.exists(fname)
    if result:
        with open(fname, "r") as fp:
            f = fp.read()
        result = "\n".join(l for l in file_data) + "\n" == f
        os.remove(fname)

    return result


class FileWriter(Actor):

    """
        Writes input 'data' to file 'basename' + some counter + '.' + suffix
        End of stream token changes file
        inputs:
            data: data
    """

    @manage(['basename', 'counter', 'suffix'])
    def init(self, basename, suffix=""):
        self.basename = basename
        self.suffix = suffix
        self.counter = 0
        self.file = None
        self.setup()

    def setup(self):
        self.use('calvinsys.io.filehandler', shorthand='file')
        fname = new_filename(self.basename, self.counter, self.suffix)
        self.counter += 1
        self.file = self['file'].open(fname, "w")

    def exception_handler(self, action, args):
        self['file'].close(self.file)
        self.file = None

    @stateguard(lambda self: not self.file)
    @condition(action_input=['data'])
    def openf(self, data):
        self.setup()
        self.file.write_line(data.encode('utf-8'))

    @stateguard(lambda self: self.file)
    @condition(action_input=['data'])
    def writef(self, data):
        self.file.write_line(data.encode('utf-8'))

    def did_migrate(self):
        self.file = None
        self.setup()

    action_priority = (writef, openf)
    requires = ['calvinsys.io.filehandler']

    test_args = [absolute_basename('test_file'), 'testing']

    test_data = ['line-1', 'line-2']

    test_set = [
        {
            'in': {'data': [file_data[0], file_data[1], EOSToken()]},
            'postcond': [verify_file]
        },
        {
            'in': {'data': [file_data[0], file_data[1], EOSToken()]},
            'postcond': [verify_file]
        }
    ]
