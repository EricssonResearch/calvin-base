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

from calvin.runtime.south.calvinsys import base_calvinsys_object

class BaseTwitter(base_calvinsys_object.BaseCalvinsysObject):
    """
    Twitter - Post updates to twitter feed
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
