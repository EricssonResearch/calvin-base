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

from calvin.runtime.south.plugins.media import camera


class Cam(object):

    """
    Capture image from device
    """

    def __init__(self, device, width, height):
        """
        Initialize camera
        """
        self.camera = camera.Camera(device, width, height)

    def get_image(self):
        """
        Captures an image
        returns: Image as jpeg encoded binary string, None if no frame
        """
        return self.camera.get_image()

    def close(self):
        """
        Uninitialize camera
        """
        self.camera.close()


class CameraHandler(object):

    def open(self, device, width, height):
        return Cam(device, width, height)

    def close(self, camera):
        camera.close()


def register(node=None, actor=None):
    """
        Called when the system object is first created.
    """
    return CameraHandler()
