
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

from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.runtime.south.plugins.async import async

class Timer(base_calvinsys_object.BaseCalvinsysObject):
    """
    Timers - Handling of system timers
    """

    init_schema = {
        "description": "Initialize timer",
        "properties" : {
            "repeats" :  {
                "description": "Should the timer automatically reset once triggered?",
                "type": "boolean"
            }
        }
    }
    
    can_read_schema = {
        "description": "True iff timer has triggered",
    }

    read_schema = {
        "description": "Ack triggered timer"
    }
    
    can_write_schema = {
        "description": "Always True"
    }
    
    write_schema = {
        "description": "Set or cancel timer; number indicates set/reset, and false cancels",
        "type": ["number", "boolean"]
    }

    def init(self, repeats=False, **kwargs):
        self._timer = None
        self._triggered = False
        self._timeout = None
        self._repeats = True

    def _timer_cb(self):
        self._triggered = True
        self.scheduler_wakeup()
        
    def can_read(self):
        return self._triggered
    
    def read(self):
        self._triggered = False
        if self._repeats :
            self._timer = async.DelayedCall(self._timeout, self._timer_cb)
    
    def write(self, set_reset_or_cancel):
        cancel_only = isinstance(set_reset_or_cancel, bool)

        # cancel timer if running
        if self._timer and self._timer.active():
            self._timer.cancel()
        
        if not cancel_only:
            self._timeout = float(set_reset_or_cancel)
            self._timer = async.DelayedCall(self._timeout, self._timer_cb)

    def can_write(self):
        # Can always stop & reset a timer
        return True
        
    def close(self):
        if self._timer:
            self._timer.cancel()
            del self._timer
            self._timer = None
        self._triggered = False
