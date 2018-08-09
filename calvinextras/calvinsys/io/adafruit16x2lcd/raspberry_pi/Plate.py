# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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

from calvinextras.calvinsys.io.adafruit16x2lcd.BaseDisplay import BaseDisplay
from calvin.runtime.south.async import threads
import Adafruit_CharLCD as LCD


class Plate(BaseDisplay):

    """
    Control Raspberry Pi Adafruit 16x2 LCD plate
    """

    def init(self, prefix=None, **kwargs):
        self._prefix = prefix
        self.lcd = LCD.Adafruit_CharLCDPlate()
        self.defer = None
        self.enable(True)

    def enable(self, enable):
        self.lcd.set_backlight(enable)
        self.clear()

    def cb_show_text(self, *args, **kwargs):
        self.defer = None

    def show_text(self, text):
        if self.defer is None:
            self.clear()
            self.defer = threads.defer_to_thread(self.lcd.message, text)
            self.defer.addCallback(self.cb_show_text)
            self.defer.addErrback(self.cb_show_text)

    def clear(self):
        self.lcd.clear()

    def can_write(self):
        return True

    def write(self, data=None):
        self.show_text(str(data))

    def close(self):
        self.enable(False)
        self.clear()
