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
    """
        A calvinsys module for posting tweets. Requires twitter credentials of the form
        { 
            "customer_key": "<key>",
            "customer_secret": "<secret>",
            "access_token_key": "<key>",
            "access_token_secret": "<secret">,
        }
        The keys and secrets should be as per the twitter api documentation.
        
        The credentials are added either as a private runtime attribute, i.e
        
        /private/web/twitter.com/
        
        or supplied by the actor before trying to tweet, i.e.
        
        actor.use('calvinsys.web.twitter', shorthand='twitter')
        actor['twitter'].set_credentials({...})
        
        Note: Currently, credentials can only be supplied once and cannot be changed once in use.
    """
    
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        
        twitter_credentials = self._node.attributes.get_private("/web/twitter.com")
        if twitter_credentials :
            self._tweeter = twitter.Twitter(twitter_credentials)
        else :
            _log.warning("Expected credentials /private/web/twitter.com not found")
            self._tweeter = None
            
    def set_credentials(self, twitter_credentials):
        if not self._tweeter:
            self._tweeter = twitter.Twitter(twitter_credentials)
            success = True
        else :
            _log.warning("Credentials already supplied - ignoring")
            success = False
        return success
        
    def post_update(self, text):
        if not self._tweeter:
            _log.warning("Credentials not set, cannot tweet")
            return
        self._tweeter.post_update(text)


def register(node, actor):
    return Twitter(node, actor)
