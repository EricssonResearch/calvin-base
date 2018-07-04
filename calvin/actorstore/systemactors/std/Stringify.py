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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import *
from calvin.actor.actor import Actor, manage, condition
from calvin.runtime.north.calvin_token import EOSToken, ExceptionToken
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Stringify(Actor):
    """
    Consume a token and stringify its value

    Input:
      in
    Output:
      out
    """

    @manage()
    def init(self, encoding=None):
        self.encoding = encoding

    @condition(['in'], ['out'])
    def stringify(self, input):
        try:
            # Always unicode
            if self.encoding:
                new_token = str(input, self.encoding)
            else:
                new_token = str(input)

            return (new_token, )
        except Exception as exc:
            _log.error("Error %s, cant decode token '%s'", str(exc), repr(input))

        return (ExceptionToken("Decode error"),)

    action_priority = (stringify, )

    test_set = [
        {
            'inports': {'in': [1, 2, 'test']},
            'outports': {'out': ['1', '2', 'test']}
        }
    ]
