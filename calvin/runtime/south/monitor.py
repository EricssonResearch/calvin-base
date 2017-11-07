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

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Event_Monitor(object):

    def __init__(self):
        super(Event_Monitor, self).__init__()
        """docstring for __init__"""

        self.endpoints = []
        self._backoff = {}
        
    def set_backoff(self, endpoint):
        self._backoff[endpoint] = 5
        print backoff
    
    def _wait(self, endpoint):
        return self._backoff.get(endpoint, 0) > 0
        
    def _decrease_backoff(self, endpoint):
        bo = self._backoff.get(endpoint, 0)
        if bo > 0:
            self._backoff[endpoint] = bo-1
    
    def _outstanding(self):
        for bo in self._backoff:
            if bo > 0:
                return True
        return False            

    def register_endpoint(self, endpoint):
        self.endpoints.append(endpoint)

    def unregister_endpoint(self, endpoint):
        self.endpoints.remove(endpoint)

    # def communicate(self, scheduler):
    #     # Communicate endpoint, see if anyone sent anything
    #     did_try = False
    #     for endp in self.endpoints:
    #         if self._wait(endp):
    #             self._decrease_backoff(endp)
    #         else:
    #             endp.communicate()
    #             did_try = True
    #     return did_try or self._outstanding()
    
    def communicate(self, scheduler):
        # Communicate endpoint, see if anyone sent anything
        did_try = False
        did_comm = False
        for endp in self.endpoints:
            if self._wait(endp):
                self._decrease_backoff(endp)
            else:
                did_comm |= endp.communicate()
                did_try = True
                
        return did_comm
    
