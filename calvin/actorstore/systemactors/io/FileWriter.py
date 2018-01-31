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
        fname = new_filename(self.basename, self.counter, self.suffix)
        self.counter += 1
        self.file = calvinsys.open(self, "io.filewriter", filename=fname, mode="w")

    def did_migrate(self):
        self.file = None
        self.setup()

    def will_end(self):
        if self.file is not None:
            calvinsys.close(self.file)
            self.file = None

    @stateguard(lambda self: self.file and calvinsys.can_write(self.file))
    @condition(action_input=['data'])
    def writef(self, data):
        calvinsys.write(self.file, data.encode('utf-8'))

    action_priority = (writef,)
    requires = ['io.filewriter']

    test_kwargs = {'basename': 'test'}
    test_calvinsys = {
        'io.filewriter': {'write': ['the quick brown fox jumped over the lazy dog']},
    }
    test_set = [
        {
            'inports': {'data': ['the quick brown fox jumped over the lazy dog']}
        }
    ]
