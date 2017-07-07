# -*- coding: utf-8 -*-

# Copyright (c) 2016-17 Ericsson AB
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


from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib


class Camera(Actor):

    """
    When input trigger goes high fetch image from given device.

    Inputs:
      trigger: binary input
    Outputs:
      image: generated image
    """

    @manage(['device', 'width', 'height', 'trigger'])
    def init(self, device=0, width=640, height=480):
        self.device = device
        self.width = width
        self.height = height
        self.trigger = None
        self.setup()

    def setup(self):
        self.use("calvinsys.media.camerahandler", shorthand="camera")
        self.use("calvinsys.media.image", shorthand="image")
        self.base64 = calvinlib.use('base64')

        self.camera = self["camera"].open(self.device, self.width, self.height)

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.camera.close()

    def will_migrate(self):
        self.camera.close()

    @stateguard(lambda self: self.trigger is True)
    @condition(action_output=['image'])
    def get_image(self):
        self.trigger = None
        img = self.camera.get_image()
        result = self.base64.encode(img)

        return (result, )

    @stateguard(lambda self: self.trigger is None)
    @condition(action_input=['trigger'])
    def trigger_action(self, trigger):
        self.trigger = True if trigger else None

    action_priority = (get_image, trigger_action)
    requires = ['calvinsys.media.image', 'base64', 'calvinsys.media.camerahandler']
