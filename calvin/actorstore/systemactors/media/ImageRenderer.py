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

from calvin.actor.actor import Actor, ActionResult, condition, manage


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
            self.image.show_image(image, self.width, self.height)
        return ActionResult(production=())

    action_priority = (render_image, )
    requires =  ['calvinsys.media.image']
