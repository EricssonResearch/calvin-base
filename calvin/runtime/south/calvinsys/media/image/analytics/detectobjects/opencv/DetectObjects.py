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

from calvin.runtime.south.calvinsys.media.image.analytics.detectobjects import BaseDetectObjects
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import async
from calvin.runtime.south.plugins.opencv import opencv
import base64


_log = get_logger(__name__)


class DetectObjects(BaseDetectObjects.BaseDetectObjects):
    """
    OpenCV implementation of detect objetcs API.
    """

    def init(self, mark_objects=False, **kwargs):
        self._haarcascade_file = kwargs.get("haarcascade_file", "")
        if not self._haarcascade_file:
            _log.warning("DetectObjects: No classifier file given - this is unlikely to work")
        self._mark_objects = mark_objects
        self._result = None

    def _detect_objects(self, b64image):
        image = base64.b64decode(b64image)
        result = None
        try:
            result = opencv.detect_objects(image=image, haarcascade_file=self._haarcascade_file, mark=self._mark_objects)
            if self._mark_objects:
                # Result is a new image with objects marked
                self._result = base64.b64encode(result)
            else:
                # Result is a list of objects found
                self._result = len(result)
        except Exception as e:
            _log.error("Failed to detect objects: {}".format(e))

    def can_write(self):
        return self._result is None

    def write(self, b64image):
        async.call_in_thread(self._detect_objects, b64image)

    def can_read(self):
        return self._result is not None
        
    def read(self):
        result = self._result
        self._result = None
        return result 

    def close(self):
        pass
        