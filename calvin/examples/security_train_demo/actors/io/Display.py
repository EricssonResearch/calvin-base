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

from calvin.actor.actor import Actor, ActionResult, condition


class Display(Actor):
    """
    Control a display
    Inputs:
      text : text to display
    """

    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.io.display", shorthand="display")
        self.display = self["display"]
        self.display.enable(True)

    def will_end(self):
        self.display.enable(False)

    def did_migrate(self):
        self.setup()

    @condition(action_input=["text"])
    def show_text(self, text):
        self.display.show_text(str(text))
        return ActionResult()

    action_priority = (show_text, )
    requires = ["calvinsys.io.display"]
