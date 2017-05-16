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

from calvin.runtime.south.plugins.io.button import button

class Button():
    
    """
    Button
    """

    def __init__(self):
        self.button = button.Button()
    
    def set_text(self, text):
        self.button.set_text(text)

    def was_triggered(self):
        return self.button.was_triggered()

    def show_button(self):
        return self.button.show_button()

    def destroy(self):
        return self.button.destroy()
    
def register(node=None, actor=None):
    """
        Called when the system object is first created.
    """
    return Button()
