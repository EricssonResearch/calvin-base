# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

import pushbullet
from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Pushbullet(object):

    """
    Post PushBullet message
    Requires pushbullet.py (pip install pushbullet.py)
    """

    def __init__(self, credentials):
        api_key = credentials.get('api_key')
        self._api = pushbullet.PushBullet(api_key)

    def get_channel(self, channel_tag):
        return self._api.get_channel(channel_tag)

    def push_to_channel(self, channel, title, text):
        async.call_from_thread(channel.push_note, title, text)