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

from calvin.runtime.south.calvinlib import base_calvinlib_object
import time
import datetime


class Time(base_calvinlib_object.BaseCalvinlibObject):
    """
    Functions for handling time.
    """

    init_schema = {
        "description": "setup time module",
        "type": "object",
        "properties": {}
    }

    timestamp = {
        "description": "get the current timestamp",
        "type": "object",
        "properties": {}
    }

    datetime = {
        "description": "get the current datetime dict",
        "type": "object",
        "properties": {}
    }

    strftime = {
        "description": "get the current formattad time",
        "type": "object",
        "properties": {
            "formating": {"type": "string"}
        }
    }

    def init(self):
        pass

    def timestamp(self):
        return time.time()

    def datetime(self):
        dt = datetime.datetime.now()
        retval = {
            'century': dt.year // 100,
            'year': dt.year % 100,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'minute': dt.minute,
            'second': dt.second,
            'timezone': None
        }
        return retval

    def strftime(self, formating):
        return time.strftime(formating, time.gmtime())
