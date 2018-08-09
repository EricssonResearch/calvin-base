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

class DummyImage(base_calvinsys_object.BaseCalvinsysObject):
    """
    DummyImage - Fetch an image from 'dummyimage.com'.
    """

    init_schema = {
        "type": "object",
        "properties": {
            "resolution": {
                "type": "string",
                "description": "Set resolution of returned image",
                "enum": ["vga", "svga", "ntsc", "pal", "hd720", "hd1080"]
            },
            "bgcolor": {
                "type": "integer",
                "minimum": 0,
                "maximum": 4096,
                "exclusiveMaximum": False
            },
            "fgcolor": {
                "type": "integer",
                "minumum": 0,
                "maximum": 4096,
                "exclusiveMaximum": False
            },
            "text": {
                "type": "string"
            }
        },
        "description": "Set resolution, colors and text to display on test image",
        "required": ["text"]
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

    def init(self, text, resolution="hd1080", fgcolor=0x0, bgcolor=0xff):
        self._text = text.replace(" ", "+")
        self._url = "https://dummyimage.com/{resolution}/{fgcolor}/{bgcolor}.jpg&text={text}".format(
            resolution=resolution,
            fgcolor="%03x" % (fgcolor,),
            bgcolor="%03x" % (bgcolor,),
            text=text
        )

        self._in_progress = None
        self._image = None
        self._ctr = 0

    def can_write(self):
        return self._in_progress is None and self._image is None

    def write(self, _):

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

        self._in_progress = threads.defer_to_thread(requests.get, self._url + "-%s" % (self._ctr,))
        self._in_progress.addCallback(_new_data)
        self._in_progress.addErrback(_no_data)
        self._ctr+=1

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
