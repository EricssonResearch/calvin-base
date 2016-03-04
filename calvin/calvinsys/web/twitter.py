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

from calvin.runtime.south.plugins.web import twitter
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


class Twitter(object):
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        private_attributes = node.attributes.get_private()
        try:
            twitter_credentials = private_attributes["web"]["twitter"]
            self._tweeter = twitter.Twitter(twitter_credentials)
        except KeyError:
            _log.warning("Expected credentials /private/web/twitter not found")
            self._tweeter = None
            
        
        
    def post_update(self, text):
        if not self._tweeter:
            _log.warning("Cannot tweet")
            return
        self._tweeter.post_update(text)


def register(node, actor):
    return Twitter(node, actor)
