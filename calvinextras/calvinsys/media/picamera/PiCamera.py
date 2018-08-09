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

import picamera

from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class PiCamera(base_calvinsys_object.BaseCalvinsysObject):
    """
    Raspberry Pi PiCamera implementation for calvinsys
    """

    init_schema = {
        "type": "object",
        "properties": {
            "mode": {
                "description": "Camera mode to set",
                "type": "string",
                "enum": [ "1920x1080", "2592x1944", "1296x972", "1296x730", "640x480"]
            },
            "height": {
                "description": "Rescale image height after capture",
                "type": "integer",
                "minimum": 1,
                "maximum": 1080
            },
            "width": {
                "description": "Rescale image width after capture",
                "type": "integer",
                "minimum": 1,
                "maximum": 1920

            },
            "label": {
                "description": "Label to add to image",
                "type": "string",
                "maxLength": 41
            },
            "rotation": {
                "description": "Rotate image (in degrees)",
                "type": "integer",
                "minimum": 0,
                "maximum": 360
            }
        },
        "required": ["mode"],
        "description": "Set up PiCamera"
    }

    can_write_schema = {
        "description": "True if device is ready for new image request",
        "type": "boolean"
    }

    write_schema = {
        "description": "Request new image",
        "type": ["null", "boolean", "string"]
    }

    can_read_schema = {
        "description": "True if new image is available for reading",
        "type": "boolean"
    }
    read_schema = {
        "description": "Read image from camera as base64 encoded image",
        "type": "string"
    }

    def init(self, mode, label=None, width=None, height=None, rotation=0, **kwargs):
        self._in_progress = None
        self._b64image = None
        mode = mode.split("x")
        self._resolution = (int(mode[0]), int(mode[1]))
        if width and height:
            self._rescale = (width, height)
        else :
            self._rescale = None
        self._label = label
        self._rotation = rotation
        self._camera = picamera.PiCamera()
        self._camera.rotation = self._rotation
        self._camera.resolution = self._resolution
        if self._label:
            self._camera.annotate_text = self._label
        self._camera.start_preview()


    def can_write(self):
        return self._b64image is None and self._in_progress is None

    def _q_read_image(self):
        import base64
        import io
        stream = io.BytesIO()
        if self._rescale:
            self._camera.capture(stream, format="jpeg", resize=self._rescale)
        else :
            self._camera.capture(stream, format="jpeg")
        stream.seek(0)
        return base64.b64encode(stream.read())


    def _p_read_image(self):
        import base64
        import io
        stream = io.BytesIO()
        with picamera.PiCamera() as cam:
            cam.rotation = self._rotation
            cam.resolution = self._resolution
            if self._label:
                cam.annotate_text = self._label
            cam.start_preview()
            if self._rescale:
                cam.capture(stream, format="jpeg", resize=self._rescale, use_video_port=True)
            else :
                cam.capture(stream, format="jpeg", use_video_port=True)
        stream.seek(0)
        return base64.b64encode(stream.read())

    def _read_image(self):
        try :
            return self._q_read_image()
        except Exception as e:
            _log.warning("Error reading image: {}".format(e))
        return ""

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
        self._camera.close()
