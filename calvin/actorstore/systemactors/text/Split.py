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


class Split(Actor):
    """
    Split string into list of strings on delimiter 'delim'. Consumes delimiter.

    Inputs:
      text : arbitrary string
    Outputs:
      lines : list of strings
    """
    @manage(['delim'])
    def init(self, delim):
        self.delim = str(delim)

    @condition(['text'], ['lines'])
    def action(self, token):
        res = token.split(self.delim)
        return (res,)

    action_priority = (action, )

    test_kwargs = {'delim': ' '}
    test_set = [
        {
            'inports': {'text': ["Five words in a list"]},
            'outports': {'lines': [["Five", "words", "in",  "a", "list"]]}
        }
    ]
