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

# import re
from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib


class RegexMatch(Actor):
    """
    Apply the regex supplied as argument to the incoming text.

    If the regex matches, the text is routed to the 'match' output,
    otherwise it is routed to the 'no_match' output.
    If a (single) capture group is present, the captured result will
    be routed to 'match' instead of the full match, but it the match
    fails, the full input text will be routed to 'no_match' just as
    if no capture group was present. Any additional capture groups
    will be ignored.

    Inputs:
      text : text to match
    Outputs:
      match    : matching text or capture if capture group present
      no_match : input text if match fails
    """
    @manage(['regex', 'result', 'did_match'])
    def init(self, regex):
        self.regex = regex
        self.result = None
        self.did_match = False
        self.setup()

    def setup(self):
        self.re = calvinlib.use('regexp')

    def did_migrate(self):
        self.setup()

    def perform_match(self, text):
        m = self.re.match(self.regex, text)
        self.did_match = m is not None
        self.result = m.groups()[0] if m and m.groups() else text

    @stateguard(lambda self: self.result is None)
    @condition(['text'], [])
    def match(self, text):
        self.perform_match(str(text))


    @stateguard(lambda self: self.result is not None and self.did_match)
    @condition([], ['match'])
    def output_match(self):
        result = self.result
        self.result = None
        return (result,)

    @stateguard(lambda self: self.result is not None and not self.did_match)
    @condition([], ['no_match'])
    def output_no_match(self):
        result = self.result
        self.result = None
        return (result,)

    action_priority = (match, output_match, output_no_match)
    requires = ['regexp']


    test_args = [".* (FLERP).* "]
    test_set = [
        {'inports': {'text': ["This is a test FLERP please ignore"]},
         'outports': {'match': ['FLERP'], 'no_match':[]}
         },
        {'inports': {'text': ["This is a test please ignore"]},
         'outports': {'match': [], 'no_match':["This is a test please ignore"]}
         }
    ]
