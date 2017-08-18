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
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import base64
from PIL import Image
from io import BytesIO

width = 640
height = 480

class Camera(object):

    """
    Capture image from device
    """

    def __init__(self, device, width, height):
        """
        Initialize camera
        """
	print "initialize picamera"
	self.camera = PiCamera()
	self.camera.resolution = (width, height)
	self.camera.rotation = 90
	#allow the camera to warm up
	time.sleep(0.1)

    def get_image(self):
        """
        Captures an image
        returns: Image as jpeg encoded binary string, None if no frame
        """
	stream = BytesIO()
	#capture into stream, use video port as it is much faster
	self.camera.capture(stream, format='jpeg', use_video_port=True)
	picture = stream.getvalue()
	return base64.b64encode(picture)

  

    def close(self):
        """
        Uninitialize camera
        """
        self.camera.close()
