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

from calvin.actor.actor import Actor, ActionResult, manage, condition

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class FacebookPicture(Actor):
    """
    Post incoming tokens (text) as twitter status
    example of a picture
        {'picture' : '/home/pi/Pictures/setup.jpg',
         'message' : 'test from calvin' }
    Input:
      picture : A JSON file with the picture absolute path and it's relative message
    """

    @manage([])
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.use('calvinsys.web.facebook', shorthand='facebook')

    @condition(action_input=['picture'])
    def post_picture(self, picture):
        self['facebook'].post_picture(picture)
        return ActionResult()

    action_priority = (post_picture,)
    requires = ['calvinsys.web.facebook']
