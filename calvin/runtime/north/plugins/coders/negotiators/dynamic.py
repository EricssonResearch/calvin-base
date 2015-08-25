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
from calvin.utilities import calvinconfig
import negotiator_base

_conf = calvinconfig.get()


class DynamicNegotiator(negotiator_base.NegotiatorBase):

    def get_coder(self, channel):
        raise NotImplemented("This is not implemented yet.")

