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

import cv2
import numpy

def detect_objects(image, haarcascade_file, mark):
    classifier = cv2.CascadeClassifier(haarcascade_file)
    with open("testimage.jpg", "w+") as fp:
        fp.write(image)
    jpg = numpy.fromstring(image, numpy.int8)
    image = cv2.imdecode(jpg, 1)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # The following line probably needs some further work
    objects = classifier.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(50,50))
    if mark:
        for (x, y, w, h) in objects :
            cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        _, new_image = cv2.imencode(".jpg", image)
        return new_image
    else :
        return objects

