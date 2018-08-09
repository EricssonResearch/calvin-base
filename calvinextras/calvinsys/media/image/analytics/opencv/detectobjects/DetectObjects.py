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

from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.async import threads
import cv2
import numpy
import base64


_log = get_logger(__name__)


class DetectObjects(base_calvinsys_object.BaseCalvinsysObject):
    """
    DetectObjects: Find (and optionally mark) preconfigured objects in image, (uses OpenCV)

    See https://github.com/opencv/opencv/tree/master/data/haarcascades for some objects classifiers
    """

    init_schema = {
        "description": "Setup DetectObjetcs",
        "type": "object",
        "properties": {
            "mark_objects": {
                "description": "Mark found objects in image",
                "type": "boolean"
            },
            "haarcascade_file": {
                "description": "Haarcascade file defining the objects",
                "type": "string"
            }
        },
        "required": ["haarcascade_file"]
    }

    can_write_schema = {
        "description": "True if ready for next analysis image"
    }

    write_schema = {
        "description": "Count objects as defined by haarcascade file. Works on b64 encoded image",
        "type": "string"
    }

    can_read_schema = {
        "description": "True iff prevoius image has finished processing"
    }

    read_schema = {
        "description": "Mark objects as defined by haarcascade file. Input b64 encoded image, return b64 encoded image with found objects marked",
        "type": ["string", "integer"]
    }

    def init(self, mark_objects=False, haarcascade_file=None):
        if not haarcascade_file:
            _log.warning("DetectObjects: No classifier file given - this is unlikely to work")
        else:
            self.classifier = cv2.CascadeClassifier(haarcascade_file)
        self._mark_objects = mark_objects
        self._result = None

    def detect_objects(self, b64image):
        def find_objects(image, haarcascade_file, mark):
            # classifier = cv2.CascadeClassifier(haarcascade_file)
            jpg = numpy.fromstring(image, numpy.int8)
            image = cv2.imdecode(jpg, 1)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # The following line probably needs some further work
            objects = self.classifier.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(50,50))
            if mark:
                for (x, y, w, h) in objects :
                    cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                _, new_image = cv2.imencode(".jpg", image)
                return new_image
            else :
                return objects

        image = base64.b64decode(b64image)
        try:
            image = cv2.imdecode(numpy.fromstring(image, numpy.int8), 1)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Probably needs some more fine-tuning
            objects = self.classifier.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(50,50))
            if self._mark_objects:
                for (x, y, w, h) in objects:
                    cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                _, new_image = cv2.imencode(".jpg", image)
                return base64.b64encode(new_image)
            else:
                return len(objects)
        except Exception as e:
            _log.error("Failed to detect objects: {}".format(e))

    def can_write(self):
        return self._result is None

    def write(self, b64image):
        def success(result):
            self._result = result

        def done(*args, **kwargs):
            self.scheduler_wakeup()
        defered = threads.defer_to_thread(self.detect_objects, b64image)
        defered.addCallback(success)
        defered.addBoth(done)

    def can_read(self):
        return self._result is not None

    def read(self):
        result = self._result
        self._result = None
        return result

    def close(self):
        pass
