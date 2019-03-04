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

from calvin.actor.actor import Actor, manage, condition, calvinlib


def value_for_key(d, keypath):
    keylist = keypath.split('.')
    res = d
    for key in keylist:
        res = res[key]
    return res


class Format(Actor):

    """
    documentation:
    - Format output according to 'fmt' using dict
    - Format string uses \"{access.key.path}\" to access dict
    ports:
    - direction: in
      help: Dictionary
      name: dict
    - direction: out
      help: Formatted string
      name: text
    requires:
    - regexp
    """

    REGEX = r"{(.+?)}"

    @manage(['fmt', 'fmtkeys'])
    def init(self, fmt):
        self.fmt = fmt
        self.regexp = calvinlib.use('regexp')
        tmp = fmt.replace(r"\{", "").replace(r"\}", "")
        self.fmtkeys = self.regexp.findall(Format.REGEX, tmp)

    @condition(['dict'], ['text'])
    def action(self, d):
        res = {}
        try:
            for fmtkey in self.fmtkeys:
                res[fmtkey] = value_for_key(d, fmtkey)
        except Exception:
            res = {}
        retval = self.fmt
        for key, value in res.items():
            retval = retval.replace('{' + key + '}', str(value))
        retval = retval.replace(r"\{", "{").replace(r"\}", "}")

        return (retval, )

    action_priority = (action, )
    


    test_kwargs = {'fmt': r"{huey.dewey.louie} \{huey.dewey.louie\}"}
    test_set = [
        {
            'inports': {'dict': [{'huey': {'dewey': {'louie': 'gotcha!'}}}]},
            'outports': {'text': ['gotcha! {huey.dewey.louie}']}
        }
    ]
