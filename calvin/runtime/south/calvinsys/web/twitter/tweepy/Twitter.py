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

from calvin.runtime.south.calvinsys.web.twitter import BaseTwitter
from calvin.runtime.south.plugins.web import twitter

class Twitter(BaseTwitter.BaseTwitter):
    """
    Calvinsys object for posting twitter updates
    """
    def init(self, consumer_key, consumer_secret, access_token_key, access_token_secret, **kwargs):
        self._twitter = twitter.Twitter({"consumer_key": consumer_key, "consumer_secret": consumer_secret,
            "access_token_key": access_token_key, "access_token_secret": access_token_secret})

    def can_write(self):
        return self._twitter is not None

    def write(self, update):
        self._twitter.post_update(update)

    def close(self):
        del self._twitter
        self._twitter = None
