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

import pygame

from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger
from calvinextras.calvinsys.media.audio.play import BasePlay

_log = get_logger(__name__)


class Play(BasePlay.BasePlay):
    """
    Implementation of Play API based on pygame - note: only suitable for audioclips around a few seconds long
    """
    def init(self, audiofile=None):
        def done(*args, **kwargs):
            self.is_playing = False

        self.audiofile = audiofile
        self.is_playing = None
        self.player = None

        defered = threads.defer_to_thread(pygame.mixer.init)
        defered.addBoth(done)

    def can_write(self):
        return self.is_playing is False

    def write(self, audiofile=None):
        def play_it(player, audiofile):
            try:
                if not player:
                    player = pygame.mixer.Sound(audiofile)
                if player:
                    player.play()
                else :
                    _log.warning("Failed to initialize audio")
                return player if self.audiofile else None # keep player if audio is given in init
            except Exception as e:
                _log.info("Error playing file: {}".format(e))

        def finished(player):
            if player:
                self.player = player

        def done(*args, **kwargs):
            self.is_playing = False
            self.scheduler_wakeup()

        self.is_playing = True

        if self.audiofile:
            audiofile = self.audiofile

        defered = threads.defer_to_thread(play_it, player=self.player, audiofile=audiofile)
        defered.addCallback(finished)
        defered.addBoth(done)
        _log.info("Done")

    def close(self):
        if self.player:
            self.mixer.quit()

