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

from calvin.runtime.south.calvinsys.media.audio.play import BasePlay
from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Play(BasePlay.BasePlay):
    """
    Implementation of Play Calvinsys API
    """
    def init(self, audiofile):
        self._playing = None
        self._player = None
        async.call_in_thread(self._init_audio, audiofile)

    def _init_audio(self, audiofile):
        try:
            pygame.mixer.init()
            self._player = pygame.mixer.Sound(audiofile)
        except Exception as e:
            _log.warning("Failed to initialize audio: {}".format(e))
            
    def can_write(self):
        return bool(self._player) and not self._playing

    def _play(self):
        self._playing = self._player.play()
        
    def write(self, _):
        self._playing = True
        async.call_in_thread(self._play)
 
    def close(self):
        if self._player is not None:
            # de init
            self.mixer.quit()
        
