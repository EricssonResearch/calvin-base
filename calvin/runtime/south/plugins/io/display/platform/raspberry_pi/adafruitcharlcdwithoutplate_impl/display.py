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

from calvin.runtime.south.plugins.io.display import base_display
from calvin.runtime.south.plugins.async import async
from Adafruit_CharLCD import Adafruit_CharLCD as LCD
import Adafruit_GPIO as aGPIO
import RPi.GPIO as GPIO

def rotate(line):
    return line[1:] + line[:1]

class TwoLineLCD(object):
    
    def __init__(self, lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight):
        self.lcd = LCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight, gpio=aGPIO.get_platform_gpio())
        self.lcd.clear()
        self._columns = lcd_columns
        self._in_progress = None

    def clear(self):
        self.lcd.clear()
    
    def cancel(self):
        if self._in_progress and self._in_progress.active():
            self._in_progress.cancel()
        self.clear()
        
    def message(self, line_1, line_2):
        self.cancel()
        if len(line_1) > self._columns:
            line_1 += " " # Padding when scrolling
        if len(line_2) > self._columns:
            line_2 += " " # Padding when scrolling
        self._in_progress = async.DelayedCall(0, self._message, line_1, line_2)
        
        
    def _message(self, line_1, line_2):
        self.lcd.home()
        self.lcd.message(line_1[:self._columns] + "\n" + line_2[:self._columns])
        if len(line_1) > self._columns:
            line_1 = rotate(line_1)
        if len(line_2) > self._columns:
            line_2 = rotate(line_2)
            
        self._in_progress = async.DelayedCall(0.5, self._message, line_1, line_2)


class Display(base_display.DisplayBase):

    """
    Control Raspberry Pi Adafruit 16x2 LCD plate
    """

    def __init__(self):
#        self.lcd = TwoLineLCD(lcd_rs=37, lcd_en=40, lcd_d4=38, lcd_d5=33, lcd_d6=36, lcd_d7=35, lcd_columns=16, lcd_rows=2, lcd_backlight=4)
        self.lcd = TwoLineLCD(lcd_rs=26, lcd_en=21, lcd_d4=20, lcd_d5=13, lcd_d6=16, lcd_d7=19, lcd_columns=16, lcd_rows=2, lcd_backlight=4)
#        self.lcd = TwoLineLCD(lcd_rs=25, lcd_en=24, lcd_d4=23, lcd_d5=17, lcd_d6=27, lcd_d7=22, lcd_columns=16, lcd_rows=2, lcd_backlight=4)

    def enable(self, enable):
        if enable:
            self.lcd.clear()
        else:
            self.lcd.cancel()

    def show(self, text, textcolor, bgcolor):
        self.show_text(text)

    def show_text(self, text):
        lines = text.split("NEW_LINE", 1)
        if len(lines) == 1:
            line_1 = lines[0]
            line_2 = ""
        else:
            line_1, line_2 = lines[0], lines[1]
         
        self.lcd.message(line_1, line_2)

    def clear(self):
        self.lcd.clear()

