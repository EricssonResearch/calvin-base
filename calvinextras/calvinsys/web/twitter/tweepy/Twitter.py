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

import time
import tweepy

from calvin.runtime.south.async import threads, async
from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class Twitter(base_calvinsys_object.BaseCalvinsysObject):
    """
    Twitter - Post updates to twitter feed
    Requires tweepy (pip install tweepy)
    """

    init_schema = {
        "type": "object",
        "properties": {
            "consumer_key": {
                "description": "Consumer (API) key, see http://apps.twitter.com",
                "type": "string"
            },
            "consumer_secret": {
                "description": "Consumer (API) secret, see http://apps.twitter.com",
                "type": "string"
            },
            "access_token_key": {
                "description": "Access token for account to use, see http://apps.twitter.com",
                "type": "string"
            },
            "access_token_secret": {
                "description": "Access token secret for account, see http://apps.twitter.com",
                "type": "string"
            }
        },
        "required": ["consumer_key", "consumer_secret", "access_token_key", "access_token_secret"],
        "description": "Set up API usage"
    }

    can_write_schema = {
        "description": "Returns True if data can be posted, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Post update to configured twitter account",
        "type": "string"
    }

    def init(self, consumer_key, consumer_secret, access_token_key, access_token_secret, **kwargs):

        def setup_twitter():
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_token_key, access_token_secret)
            return tweepy.API(auth_handler=auth, wait_on_rate_limit=True)

        def done(api):
            self.twitter = api
            _log.info("Twitter setup done")
            self.busy = False

        _log.info("Setting up twitter")
        self.busy = True
        defer = threads.defer_to_thread(setup_twitter)
        defer.addCallback(done)

    def can_write(self):
        return not self.busy

    def write(self, message):
        def post_update(msg):
            try:
                self.twitter.update_status(msg)
            except Exception as e:
                _log.warning("Failed to post update: {}".format(str(e)))

        def done(*args, **kwargs):
            self.last_message = time.time()
            self.busy = False
            _log.info("Message posted")
        self.busy = True
        defer = threads.defer_to_thread(post_update, message)
        defer.addBoth(done)

    def close(self):
        self.busy = True
        self._twitter = None
