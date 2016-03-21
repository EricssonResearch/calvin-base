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


import cv2
import numpy

class Camera(object):

    """
    Capture image from device
    """

    def __init__(self, device, width, height):
        """
        Initialize camera
        """
        self.cap = cv2.VideoCapture(device)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, height)

    def get_image(self):
        """
        Captures an image
        returns: Image as jpeg encoded binary string, None if no frame
        """
        ret, frame = self.cap.read()
        if ret:
            ret, jpeg = cv2.imencode(".jpg", frame)
            if ret:
                data = numpy.array(jpeg)
                return data.tostring()

    def close(self):
        """
        Uninitialize camera
        """
        self.cap.release()