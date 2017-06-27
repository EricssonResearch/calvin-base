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

from calvin.runtime.south.plugins.web import pbullet
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class Pushbullet(base_calvinsys_object.BaseCalvinsysObject):
    """
    Pushbullet - Post messages to pushbullet channel
    """

    init_schema = {
        "type": "object",
        "properties": {
            "api_key": {
                "description": "API key, see https://www.pushbullet.com/account",
                "type": "string"
            },
            "channel_tag": {
                "description": "Pushbullet to post to, see http://www.pushbullet.com",
                "type": "string"
            }
        },
        "required": ["api_key", "channel_tag"],
        "description": "Setup up api key and tag of channel to use for pushbullet messages"
    }
    
    can_write_schema = {
        "description": "Returns True if data can be posted, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Post update to configured pushbullet channel",
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "title of message"},
            "message": {"type": "string", "description": "message to post to channel"}
        }
    }

    def init(self, api_key, channel_tag):
        try:
            self._pbullet = pbullet.Pushbullet({"api_key": api_key})
        except Exception as e:
            self._pbullet = None
            _log.error("Could not connect to pushbullet: {}".format(e))
            return
        self._channel = None
        self._set_channel(self._pbullet.get_channel(channel_tag))

    def _set_channel(self, channel_tag):
        self._channel = channel_tag
        
    def can_write(self):
        return self._pbullet is not None and self._channel is not None
        
    def write(self, data):
        message = data.get("message")
        title = data.get("title")
        try:
            self._pbullet.push_to_channel(self._channel, title, message)
        except Exception as e:
            _log.error("Could not push to channel: {}".format(e))
        
    def close(self):
        del self._channel
        self._channel = None
        del self._pbullet
        self._pbullet = None
