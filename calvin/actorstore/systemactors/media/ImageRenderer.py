# -*- coding: utf-8 -*-

# Copyright (c) 2015-17 Ericsson AB
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

from calvin.utilities.calvinlogger import get_actor_logger
from calvin.actor.actor import Actor, condition, manage, calvinlib

_log = get_actor_logger(__name__)


class ImageRenderer(Actor):

    """
    Render image.

    Inputs:
      image: image to render
    """

    @manage(['width', 'height'])
    def init(self, width=640, height=480):
        self.width = width
        self.height = height
        self.setup()

    def setup(self):
        self.use("calvinsys.media.image", shorthand="image")
        self.base64 = calvinlib.use('base64')
        self.image = self["image"]

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.image.close()

    def will_migrate(self):
        self.image.close()

    @condition(action_input=('image',))
    def render_image(self, image):
        if image is not None:
            self.image.show_image(self.base64.decode(image), self.width, self.height)

    action_priority = (render_image, )
    requires =  ['calvinsys.media.image', 'base64']
