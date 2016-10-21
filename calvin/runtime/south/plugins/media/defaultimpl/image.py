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
from StringIO import StringIO
import cv2
import os
import numpy
from PIL import Image as PIL_Image


class Image(object):

    """
    Image object
    """

    def __init__(self):
        self.display = None

    def show_image(self, image, width, height):
        """
        Show image
        """
        size = (width, height)
        self.display = pygame.display.set_mode(size, 0)
        self.snapshot = pygame.surface.Surface(size, 0, self.display)
        img = pygame.image.load(StringIO(image))
        self.display.blit(img, (0, 0))
        pygame.display.flip()

    def detect_face(self, image):
        linux_prefix = "/usr/share/opencv"
        mac_prefix = "/usr/local/share/OpenCV"
        suffix = "/haarcascades/haarcascade_frontalface_default.xml"
        linux_path = linux_prefix + suffix
        mac_path = mac_prefix + suffix
        
        if os.path.exists(linux_path) :
            cpath = linux_path
        elif os.path.exists(mac_path) :
            cpath = mac_path
        else :
            raise Exception("No Haarcascade found")
        classifier = cv2.CascadeClassifier(cpath)

        jpg = numpy.fromstring(image, numpy.int8)
        image = cv2.imdecode(jpg, 1)
        faces = classifier.detectMultiScale(image)
        if len(faces) > 0 :
            for (x,y,w,h) in faces :
                if w < 120 :
                    # Too small to be a nearby face
                    continue
                return True
        return False

    def to_string(self, image, format):
        buffer = StringIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    def from_string(self, img_str):
        buffer = StringIO(img_str)
        image = self.open(buffer)
        return image

    def new(self, mode, size):
        return PIL_Image.new(mode, size)

    def open(self, fp):
        return PIL_Image.open(fp)

    def close(self):
        """
        Close display
        """
        if not self.display is None:
            pygame.display.quit()
