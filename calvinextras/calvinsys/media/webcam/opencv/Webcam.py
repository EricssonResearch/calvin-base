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

from calvinextras.calvinsys.media.webcam import BaseWebcam
from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Webcam(BaseWebcam.BaseWebcam):
    """
    Implementation of Webcam Calvinsys API
    """
    def init(self, width, height, device=0, **kwargs):
        self._webcam = cv2.VideoCapture(device)
        self._webcam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._in_progress = None
        self._b64image = None

    def can_write(self):
        return self._b64image is None and self._in_progress is None

    def _read_image(self):
        import base64
        status, frame = self._webcam.read()
        barr = None
        if status:
            status, image = cv2.imencode(".jpg", frame)
        if status :
            barr = image.tostring()
        return base64.b64encode(barr)

    def _image_ready(self, image, *args, **kwargs):
        self._b64image = image
        self._in_progress = None
        self.scheduler_wakeup()

    def _image_error(self, *args, **kwargs):
        self._in_progress = None
        self.scheduler_wakeup()

    def write(self, _):
        self._in_progress = threads.defer_to_thread(self._read_image)
        self._in_progress.addCallback(self._image_ready)
        self._in_progress.addCallback(self._image_error)

    def can_read(self):
        return self._b64image is not None and self._in_progress is None

    def read(self):
        b64image = self._b64image
        self._b64image = None
        return b64image

    def close(self):
        if self._in_progress:
            self._in_progress.cancel()
        self._webcam.release()
        self._webcam = None

