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
from calvin.runtime.south.async import threads, async
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class Pushbullet(base_calvinsys_object.BaseCalvinsysObject):
    """
    Pushbullet - Post messages to pushbullet channel
    Requires pushbullet.py (pip install pushbullet.py)
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
        "type": ["object", "string"],
        "properties": {
            "title": {"type": "string", "description": "title of message"},
            "message": {"type": "string", "description": "message to post to channel"}
        }
    }

    def init(self, api_key, channel_tag, title=None):
        def init_pb():
            try:
                # pushbullet = pbullet.Pushbullet({"api_key": api_key})
                pb_api = pushbullet.PushBullet(api_key)
                ch = pb_api.get_channel(channel_tag)
                return (pb_api, ch)
            except Exception as e:
                _log.error("Failed to initialize pushbullet: {}".format(e))

        def done(pb_chan):
            self.pushbullet, self.channel = pb_chan
            self.busy = False

        self.title = title
        self.busy = True
        in_progress = threads.defer_to_thread(init_pb)
        in_progress.addCallback(done)


    def can_write(self):
        return not self.busy

    def write(self, data):
        def send():
            try:
                self.channel.push_note(title, message)
            except Exception as e:
                _log.error("Failed to send pushbullet: {}".format(e))
                done()

        def done(*args, **kwargs):
            self.busy = False

        if isinstance(data, basestring):
            message = data
            title = self.title
        else :
            message = data.get("message")
            title = data.get("title")

        self.busy = True
        in_progress = threads.defer_to_thread(send)
        in_progress.addBoth(done)

    def close(self):
        del self.channel
        self.channel = None
        del self.pushbullet
        self.pushbullet = None
