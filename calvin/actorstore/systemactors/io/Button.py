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

class Button(Actor):
    """
    Creates a button.

    Output:
      trigger : Button was pressed
    """
    
    @manage(include = ["text"])
    def init(self, text="Button"):
        self.text = text
        self.use("calvinsys.io.button", shorthand="button")
        self.button = self["button"]
        self.button.set_text(text)
    
    def will_migrate(self):
        self.button.destroy()

    def will_start(self):
        self.button.show_button()

    @stateguard(lambda self: self.button and self.button.was_triggered())
    @condition([], ["trigger"])
    def trigger(self):
        return (1,)
        
    action_priority = (trigger, )
    requires = ['calvinsys.io.button']
    
    
