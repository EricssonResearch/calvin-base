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

# encoding: utf-8

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class Jq(Actor):

    """
    Transform object with jq-script
    Parameters:
        script: a jq-script
        vars: Any variables that should be substituted in the script, default {}
        mode: any of all (each input gives list of all transforms), first (each input gives first transform), split (each input gives transforms as separate outputs)

    Inputs:
      value: json-typed object
    Outputs:
      value: the transformed value
    """

    @manage()
    def init(self, script, vars, mode):
        self.script = script
        self.vars = vars if vars else {}
        self.mode = mode
        self.outputs = []
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.jq = calvinlib.use('collections.jq')
        try:
            self.cscript = self.jq.compile(self.script, self.vars)
        except:
            _log.exception("Failed compile jq script")
            self.cscript = None

    @stateguard(lambda actor: actor.outputs)
    @condition(action_output=['value'])
    def send(self):
        return (self.outputs.pop(0), )

    @condition(['value'])
    def transform(self, value):
        if self.cscript is None:
            return
        try:
            if self.mode == "all":
                self.outputs.append(self.cscript.all(value))
            elif self.mode == "first":
                self.outputs.append(self.cscript.first(value))
            elif self.mode == "split":
                self.outputs.extend(self.cscript.all(value))
        except:
            _log.exception("Failed apply jq script")

    action_priority = (send, transform)
    requires = ["collections.jq"]

    test_args = [".", {}, "all"]
    test_set = [
        {
            'setup': [lambda self: self.init('.', {}, "first")],
            'inports': {'value': [1, 2, 3]},
            'outports': {'value': [1, 2, 3]},
        },
        {
            'setup': [lambda self: self.init('. + {"d": $d}', {"d": 4}, "first")],
            'inports': {'value': [{"a": 1}, {"b": 2}, {"c": 3}]},
            'outports': {'value': [{"a": 1, "d": 4}, {"b": 2, "d": 4}, {"c": 3, "d": 4}]},
        },
        {
            'setup': [lambda self: self.init('.a[]', {}, "first")],
            'inports': {'value': [{"a": [1]}, {"a": [2, 1]}, {"a": [3, 2, 1]}]},
            'outports': {'value': [1, 2, 3]},
        },
        {
            'setup': [lambda self: self.init('.a[]', {}, "split")],
            'inports': {'value': [{"a": [1]}, {"a": [2, 1]}, {"a": [3, 2, 1]}]},
            'outports': {'value': [1, 2, 1, 3, 2, 1]},
        },
        {
            'setup': [lambda self: self.init('.a[]', {}, "all")],
            'inports': {'value': [{"a": [1]}, {"a": [2, 1]}, {"a": [3, 2, 1]}]},
            'outports': {'value': [[1], [2, 1], [3, 2, 1]]},
        },
    ]
