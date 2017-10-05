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


class Length(Actor):
    """
    Return length of string

    Inputs:
      string : arbitrary string
    Outputs:
      length :
    """
    @manage()
    def init(self):
        pass

    @condition(['string'], ['length'])
    def action(self, token):
        return (len(token),)

    action_priority = (action, )

    test_args = []
    test_kwargs = {}

    test_set = [
        {
            'inports': {'string': ["", "a", "bb", "\r\n"]},
            'outports': {'length': [0, 1, 2, 2]},
        },
    ]
