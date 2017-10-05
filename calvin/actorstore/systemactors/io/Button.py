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

class Button(Actor):
    """
    Handle a button and trigger on state changes.

    Output:
      state : Button state 1=pressed, 0=not pressed
    """

    @manage(include = ["text", "button"])
    def init(self, text="Button"):
        self.button = None
        self.text = text
        self.button = calvinsys.open(self, "io.button", text=self.text)

    @stateguard(lambda self: self.button and calvinsys.can_read(self.button))
    @condition([], ["state"])
    def trigger(self):
        return (calvinsys.read(self.button),)

    action_priority = (trigger, )
    requires = ['io.button']


    test_kwargs = {'text': "Button"}
    test_calvinsys = {'io.button': {'read': [1,0,1,0,0,1,0,1]}}
    test_set = [
        {
            'outports': {'state': [1,0,1,0,0,1,0,1]}
        }
    ]
