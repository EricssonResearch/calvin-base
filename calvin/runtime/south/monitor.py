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

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Event_Monitor(object):

    def __init__(self):
        super(Event_Monitor, self).__init__()
        """docstring for __init__"""

        self.endpoints = []
        self._backoff = {}
        
    def set_backoff(self, endpoint):
        _, bo = self._backoff.get(endpoint, (0, 0))
        bo = min(1.0, 0.1 if bo < 0.1 else bo * 2.0)
        self._backoff[endpoint] = (time.time() + bo, bo)
        
    def clear_backoff(self, endpoint):
        self._backoff.pop(endpoint, None)
        
    def next_slot(self):
        if self._backoff:
            return min(self._backoff.values(), key=lambda x : x[0])
        return None

    def _check_backoff(self):
        current = time.time()
        for ep in self._backoff.keys():
            tc = self._backoff[ep][0]
            if tc < current:
                self.clear_backoff(ep)

    def register_endpoint(self, endpoint):
        self.endpoints.append(endpoint)

    def unregister_endpoint(self, endpoint):
        self.endpoints.remove(endpoint)
        self.clear_backoff(endpoint)

    def communicate(self, scheduler):
        """Communicate over all endpoints, return True if at least one send something."""
        # Update the backoff dictionary containing endpoints that should NOT communicate.
        self._check_backoff()
        did_comm = False
        # Loop over all endpoints, skip those in backoff dictionary
        for endp in self.endpoints:
            if not endp in self._backoff:
                did_comm |= endp.communicate()
                
        return did_comm
    
