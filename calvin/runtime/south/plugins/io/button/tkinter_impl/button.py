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
import thread
import threading
import Queue

class Button():
    
    def __init__(self):
        self.text = "Button"
        self.lock = threading.Lock()
        self.button = None
        self.button_showing = False
        self.button_presses = Queue.Queue()
        self.btthread = None

    def set_text(self, text):
        self.text = text

    def was_triggered(self):
        if self.button_presses.empty() is False:
            return self.button_presses.get_nowait()
        else:
            return False
        
    def show_button(self):
        self.btthread = thread.start_new_thread(self.tkinter_thread, (self.text,))

    def destroy(self):
        with self.lock:
            self.button_showing = False

    def tkinter_button_callback(self):
        self.button_presses.put(True)

    def tkinter_thread(self, text):
        with self.lock:
            self.button_showing = True
        self.master = Tkinter.Tk() 
        # Make it impossible to close the window
        def close_callback():
            pass
        self.master.protocol("WM_DELETE_WINDOW", close_callback)
        self.button = Tkinter.Button(self.master, text=text, command=self.tkinter_button_callback)
        self.button.pack()
        while 1:
            with self.lock:
                if self.button_showing:
                    self.master.update()
                else:
                    self.master.destroy()
                    break
