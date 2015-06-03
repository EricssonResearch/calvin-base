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

        self.out_endpoints = []

    def register_out_endpoint(self, endpoint):
        self.out_endpoints.append(endpoint)

    def unregister_out_endpoint(self, endpoint):
        self.out_endpoints.remove(endpoint)

    def loop(self, scheduler):
        # Communicate endpoint, see if anyone sent anything
        return any([endp.communicate() for endp in self.out_endpoints])
