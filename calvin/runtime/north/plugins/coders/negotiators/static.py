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

from calvin.runtime.north.plugins.coders.messages import message_coder_factory
from calvin.utilities.calvinlogger import get_logger
import negotiator_base


_log = get_logger(__name__)


class StaticNegotiator(negotiator_base.NegotiatorBase):

    def get_coder(self, prio_list):
        available_coders = message_coder_factory.get_prio_list()
        if prio_list:
            # pick first common coder
            coder = [c for c in prio_list if c in available_coders ][0]
        else :
            # Available is in order of priority
            coder = available_coders[0]

        if not coder :
            # No coder found, i.e. at least one list was empty (should never happen)
            _log.warning("No available coder found, using json")
            coder = "json"
        
        return message_coder_factory.get(coder)

    def get_list(self):
        return message_coder_factory.get_prio_list()
