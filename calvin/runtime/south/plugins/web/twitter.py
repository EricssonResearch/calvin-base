# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

import tweepy
from calvin.runtime.south.plugins.async import async
from calvin.runtime.south.plugins.async import threads
from calvin.utilities.calvinlogger import get_logger
from datetime import datetime

_log = get_logger(__name__)


class Twitter(object):

    """
    Post twitter message
    Requires tweepy (pip install tweepy)
    """

    def __init__(self, credentials):
        self._in_progress = None
        self._next_message = None
        self._previous_message = None
        auth = tweepy.OAuthHandler(credentials['consumer_key'], credentials['consumer_secret'])
        auth.set_access_token(credentials['access_token_key'], credentials['access_token_secret'])
        self._api = tweepy.API(auth)
        self._delayed_call = None
        self._time_last_message = None

    def cb_post_update(self, *args, **kwargs):
        if self._next_message:
            text = self._next_message
            self._next_message = None
            self._post_update(text)
        else:
            self._in_progress = None

    def cb_error(self, *args, **kwargs):
        _log.error("%r %r" % (args, kwargs))
        self._in_progress = None

    def _post_update(self, text):
        if not self._in_progress:
            self._in_progress = threads.defer_to_thread(self._api.update_status, status=text)
            self._in_progress.addCallback(self.cb_post_update)
            self._in_progress.addErrback(self.cb_error)
            self._time_last_message = datetime.now()
            self._previous_message = text
        else:
            self.next_message = text

    def post_update(self, text):
        try:
            if text != self._previous_message:
                if self._delayed_call:
                    # update in progress, cancel it
                    self._delayed_call.cancel()

                delay_call = False
                if self._time_last_message:
                    # limit the rate of updates to at most 1 per 10 sec.
                    d = datetime.now() - self._time_last_message
                    if d.seconds < 10:
                        delay_call = True

                if delay_call:
                    self._delayed_call = async.DelayedCall(10, self._post_update, text=text)
                else:
                    self._post_update(text)
            else:
                _log.info("Skipping duplicate message '%s'" % (text,))
        except Exception as e:
            _log.error("Failed to output tweet %s" % e)
