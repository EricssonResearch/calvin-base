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

from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger
import sense_hat


_log = get_logger(__name__)

_sensehat = None

def get_sensehat():
    global _sensehat
    if not _sensehat :
        _sensehat = sense_hat.SenseHat()
    return _sensehat

class SenseHat(object):

    def __init__(self, textcolor=None, backgroundcolor=None, rotation=None):
        self._sensehat = get_sensehat()
        self._textcolor = textcolor or (0xff, 0xff, 0xff)
        self._backgroundcolor = backgroundcolor or (0,0,0)
        self._rotation = rotation or 0
        if rotation:
            self._sensehat.set_rotation(r=rotation, redraw=True)

    def read_temperature(self, cb):
        d = threads.defer_to_thread(self._sensehat.get_temperature)
        d.addBoth(cb)

    def read_humidity(self, cb):
        d = threads.defer_to_thread(self._sensehat.get_humidity)
        d.addBoth(cb)

    def read_pressure(self, cb):
        d = threads.defer_to_thread(self._sensehat.get_pressure)
        d.addBoth(cb)

    def show_message(self, msg, cb):
        d = threads.defer_to_thread(self._sensehat.show_message, text_string=msg, text_colour=self._textcolor,
            back_colour=self._backgroundcolor)
        d.addBoth(cb)
