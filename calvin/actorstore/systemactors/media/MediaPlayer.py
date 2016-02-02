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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class MediaPlayer(Actor):

    """
    Play media file  <mediafile>.

    Inputs:
      play: Play <mediafile> when True
    """

    @manage(['media_file'])
    def init(self, media_file):
        self.media_file = media_file
        self.setup()

    def setup(self):
        self.use("calvinsys.media.mediaplayer", shorthand="player")
        self.player = self["player"]

    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        self.player.close()

    def will_end(self):
        self.player.close()

    @condition(['play'], [])
    @guard(lambda _, play: play)
    def play(self, play):
        self.player.play(self.media_file)
        return ActionResult(production=())

    @condition(['play'], [])
    @guard(lambda _, play: not play)
    def ignore(self, _):
        return ActionResult(production=())

    action_priority = (ignore, play, )
    requires =  ['calvinsys.media.mediaplayer']
