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

import time
from calvin.runtime.south.calvinsys import base_calvinsys_object

class Timer(base_calvinsys_object.BaseCalvinsysObject):
    """
    Timers - Handling of system timers
    """

    init_schema = {
        "description": "Initialize timer",
        "properties" : {
            "repeats" :  {
                "description": "Should the timer automatically reset once acknowledged (read)?",
                "type": "boolean"
            },
            "period" : {
                "description": "Timeout, in seconds. If set to 0 timer triggers immediately",
                "type": "number"
            }
        }
    }

    can_read_schema = {
        "description": "True if timer has triggered",
    }

    read_schema = {
        "description": "Acknowledge triggered timer"
    }

    can_write_schema = {
        "description": "False if trigger is armed or trigger not acknowledged"
    }

    write_schema = {
        "description": "Set timeout",
        "type": ["number"]
    }

    def init(self, repeats=False, period=None, **kwargs):
        self._timeout = period
        self._armed = False
        self._triggered = False
        self._repeats = repeats
        # Don't start timer on creation unless period is given
        if period is not None:
            self._set_timer(self._timeout)
    
    def _set_timer(self, timeout):
        self._armed = True
        self._next_time = time.time() + timeout
        self.calvinsys.schedule_timer(self, timeout)
        
    # Prvate method called by calvinsys
    def _fire(self):
        self._triggered = True
        self._armed = False
        self.scheduler_wakeup()

    def can_read(self):
        return self._triggered

    def read(self):
        self._triggered = False
        if self._repeats:
            self._set_timer(self._timeout)

    def write(self, timeout):
        if not self.can_write():
            return
        self._timeout = timeout
        self._set_timer(self._timeout)

    def can_write(self):
        return not (self._triggered or self._armed)

    def close(self):
        if self._armed:
            self._armed = False
        self._triggered = False

    # Serialize/deserialize calvinsys
    def serialize(self):
        return {"triggered": self._triggered, "timeout": self._timeout,
                "repeats": self._repeats, "nexttrigger": self._next_time if self._armed else None}

    # FIXME: Migrating a triggered but not ack'd timer require that its actor be scheduled on wakeup. 
    #        I guess, but haven't verified that it is OK to call scheduler_wakeup() before returning.
    def deserialize(self, state, **kwargs):
        self._triggered = state["triggered"]
        self._timeout = state["timeout"]
        self._repeats = state["repeats"]
        if state["nexttrigger"]:
            timeout = state["nexttrigger"] - time.time()
            self._set_timer(max(timeout, 0))
        else:
            self._armed = False
        return self
