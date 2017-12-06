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


class Mustache(Actor):

    """
    Formats string based on template and incoming dictionary

    Format string uses \"{{access.key.path}}\" to access dict
    Also refer to Mustache documentation (http://mustache.github.io/)

    Inputs:
      dict :
    Outputs:
      text : formatted string
    """

    @manage(['fmt'])
    def init(self, fmt):
        self.fmt = fmt
        self.setup()

    def setup(self):
        self.mustache = calvinlib.use("mustache")

    def did_migrate(self):
        self.setup()

    @condition(['dict'], ['text'])
    def action(self, d):
        text = self.mustache.render(self.fmt, d)
        return (text, )

    action_priority = (action, )
    requires = ["mustache"]


    test_kwargs = {'fmt': "City:{{city}} Country:{{country}} Weather:{{weather}} Temperature:{{temperature}} Humidity:{{humidity}} Pressure:{{pressure}}"}
    test_set = [
        {
            'inports': {'dict': [{'city': u'Manchester', 'temperature': 7.84, 'country': u'GB', 'humidity': 87, 'pressure': 1033, 'weather': u'overcast clouds'}]},
            'outports': {'text': ["City:Manchester Country:GB Weather:overcast clouds Temperature:7.84 Humidity:87 Pressure:1033"]}
        }
    ]
