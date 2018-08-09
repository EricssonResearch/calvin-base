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

import requests
import requests.auth
import base64

from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class AxisCamera(base_calvinsys_object.BaseCalvinsysObject):
    """
    AxisCamera - Fetch image from an Axis IP Camera. Requires username and password and assumes old VAPIX '/axis-cgi/jpg/image.cgi' API
    """

    init_schema = {
        "type": "object",
        "properties": {
            "username": {
                "description": "Username to use when fetching image",
                "type": "string"
            },
            "password": {
                "type": "string",
                "description": "Password of user"
            },
            "address" : {
                "type": "string",
                "description": "Address of camera (usually an IP address)"
            },
            "resolution": {
                "type": "string",
                "description": "Set resolution of returned image",
                "enum": ["1280x1024", "1280x960", "1280x720", "768x576", "4CIF", "704x576", "704x480", "VGA"
                         "640x480", "640x360", "2CIFEXP", "2CIF", "704x288", "704x240", "480x360", "CIF", "384x288",
                         "352x288", "352x240", "320x240", "240x180", "QCIF", "192x144","176x144", "176x120","160x120"]
            },
            "colorlevel": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "exclusiveMaximum": False
            },
            "rotation": {
                "type": "integer",
                "multipleOf": 90,
                "minumum": 0,
                "maximum": 360,
                "exclusiveMaximum": True
            }
        },
        "required": ["username", "password", "address"],
        "description": "Set username, password and address of Camera"
    }

    can_write_schema = {
        "description": "True iff no image fetching is in progress",
        "type": "boolean"
    }

    write_schema = {
        "description": "Start fetching of image. Input is ignored",
        "type": ["string", "null", "boolean"],
    }

    can_read_schema = {
        "description": "True iff image is available for reading",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read image data, returns base64 encoded string",
        "type" : "string"
    }

    def init(self, username, password, address, resolution="CIF", colorlevel=0, rotation=180):
        self._username = username
        self._password = password
        self._address = address
        self._in_progress = None
        self._image = None

        self._params = "resolution={resolution}&colorlevel={colorlevel}&rotation={rotation}".format(
            resolution=resolution,
            colorlevel=colorlevel,
            rotation=rotation
        )

    def can_write(self):
        return self._in_progress is None

    def write(self, _):
        assert self._in_progress is None
        def _no_data(*args, **kwargs):
            self._image = None
            self._in_progress = None
            self.scheduler_wakeup()

        def _new_data(req, **kwargs):
            data = req.content
            try:
                self._image = base64.b64encode(data)
            except Exception as e:
                print("Image encode error: {}".format(e))
            self._in_progress = None
            self.scheduler_wakeup()

        url = "http://{address}/axis-cgi/jpg/image.cgi?{params}".format(address=self._address, params=self._params)
        self._in_progress = threads.defer_to_thread(requests.get, url, auth=requests.auth.HTTPBasicAuth(self._username, self._password))
        self._in_progress.addCallback(_new_data)
        self._in_progress.addErrback(_no_data)

    def can_read(self):
        return self._image is not None

    def read(self):
        image = self._image
        self._image = None
        return image

    def close(self):
        self._username = None
        self._password = None
        if self._in_progress:
            self._in_progress.cancel()
        self._image = None
