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

import Tkinter
import Queue
from twisted.internet import tksupport

def close_callback():
    pass

active_buttons = 0
root = None

class Button():
    
    def __init__(self):
        self.text = "Button"
        self.button = None
        self.button_showing = False
        self.button_presses = Queue.Queue()

    def set_text(self, text):
        self.text = text

    def was_triggered(self):
        if self.button_presses.empty() is False:
            return self.button_presses.get_nowait()
        else:
            return False

    def destroy(self):
        global active_buttons
        global root

        self.button.pack_forget()
        self.button_showing = False
        active_buttons -= 1
        if active_buttons <= 0:
            tksupport.uninstall()
            root.destroy()
            root = None

    def tkinter_button_callback(self):
        self.button_presses.put(True)

    def show_button(self):
        global active_buttons
        global root
        
        if not root:
            root = Tkinter.Tk() 
            root.protocol("WM_DELETE_WINDOW", close_callback)
        if active_buttons is 0:
            tksupport.install(root)

        self.button = Tkinter.Button(root, text=self.text, command=self.tkinter_button_callback)
        self.button.pack()
        active_buttons += 1
