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

import cbor
from message_coder import MessageCoderBase

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

# set of functions to encode/decode data tokens to/from a cbor description
class MessageCoder(MessageCoderBase):

    def encode(self, data):
        return cbor.dumps(data)

    def decode(self, data):
        return cbor.loads(data)
