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


import pygame


class MediaPlayer(object):

    """
    Play media file
    """

    def __init__(self):
        self.channel = None
        pygame.mixer.init()

    def play(self, media_file):
        """
        Play media file
        """
        self.player = pygame.mixer.Sound(media_file)
        if self.channel is None or not self.channel.get_busy():
            self.channel = self.player.play()

    def close(self):
        """
        Close player
        """
        if not self.channel is None:
            self.channel.stop()
