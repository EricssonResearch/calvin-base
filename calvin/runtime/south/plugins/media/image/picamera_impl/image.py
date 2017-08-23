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

	self.display = pygame.display.set_mode(size, 0)
        self.snapshot = pygame.surface.Surface(size, 0, self.display)
        img = pygame.image.load(StringIO(image))
        self.display.blit(img, (0, 0))
        pygame.display.flip()

	# define text and colors
	dgryColor = pygame.Color(64,64,64)
	greenColor = pygame.Color(0,255,0)
	yellowColor = pygame.Color(255,255,0)
	redColor = pygame.Color(255,0,0)
	blueColor = pygame.Color(0,0,255)
	whiteColor = pygame.Color(255,255,255)
	greyColor = pygame.Color(128,128,128)
	blackColor = pygame.Color(0,0,0)
	purpleColor = pygame.Color(255,0,255)
	lgryColor = pygame.Color(192,192,192)
	msg = "The weather at the next station is: H:50, P: 34, T:22"
	fsize = 16
	textcolor = 5 # 0 to 9
	backcolor = 0 # 0 to 9, -1 for no background
	fx = 10  # x position of text
	fy = 620 # y postion of text        size = (width, height)
	#put text on image
	colors = [dgryColor,yellowColor,redColor,greenColor,blueColor,whiteColor,greyColor,blackColor,purpleColor,lgryColor]
	tcolor = colors[textcolor]
	lt = (len(msg) * (fsize/2)) + fsize
	if backcolor > -1:
   	   bcolor = colors[backcolor]
	   pygame.draw.rect(windowSurfaceObj,bcolor,Rect(fx,fy, lt, fsize))
	fontObj = pygame.font.Font('freesansbold.ttf',fsize)
	msgSurfaceObj = fontObj.render(msg, False,tcolor)
	msgRectobj = msgSurfaceObj.get_rect()
	msgRectobj.topleft =(fx,fy)        

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

    def close(self):
        """
        Close display
        """
        if not self.display is None:
            pygame.display.quit()
