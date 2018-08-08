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

from calvin.actor.actor import Actor, manage, condition, calvinsys, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Pushbullet(Actor):
    """
    Post incoming tokens (text) to runtime specific pushbullet channel with given title

    Input:
      message : A message
    """

    @manage(["title"])
    def init(self, title):
        self.title = title
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self._pb = calvinsys.open(self, "web.pushbullet.channel.post")

    def teardown(self):
        calvinsys.close(self._pb)

    def will_migrate(self):
        self.teardown()

    def will_end(self):
        self.teardown()

    @stateguard(lambda self: self._pb and calvinsys.can_write(self._pb))
    @condition(action_input=['message'])
    def post_update(self, message):
        calvinsys.write(self._pb, {"message": message, "title": self.title})

    action_priority = (post_update,)
    requires = ['web.pushbullet.channel.post']


    test_kwargs = {'title': "Some Title"}
    test_calvinsys = {'web.pushbullet.channel.post': {'write': [{'message': 'A message', 'title': 'Some Title'}]}}
    test_set = [
        {
            'inports': {'message': ["A message"]}
        }
    ]
