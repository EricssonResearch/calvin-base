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

from calvin.runtime.south.plugins.io.stdout import base_stdout
from calvin.runtime.south.plugins.async import http_client
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class StandardOut(base_stdout.BaseStandardOut):

    """
    Rest-implementation of StandardOut
    """
    def enable(self):
        # Fetch destination from private attributes
        self.destination = self.config.get("url", None)
        self.destination = self.destination.encode("utf-8")
        if not self.destination:
            _log.error("stdout: no destination url given - using print fallback")
        else:
            callbacks = {'receive-headers': [CalvinCB(self._receive_headers)],
                         'receive-body': [CalvinCB(self._receive_body)]}
            self._client = http_client.HTTPClient(callbacks)

    
    def _receive_headers(self, ignored=None):
        pass
        
    def _receive_body(self, ignored=None):
        pass
        
    def disable(self):
        self._client = None
        
    def write(self, text):
        if self.destination:
            self._client.request("POST", self.destination, {}, {}, text)
        else :
            print text,
    
    def writeln(self, text):
        self.write(text +  "\n")
