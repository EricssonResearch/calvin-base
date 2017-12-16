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
from calvin.utilities.calvinlogger import get_logger
import time
import datetime


_log = get_logger(__name__)


class Time(base_calvinlib_object.BaseCalvinlibObject):
    """
    Functions for formatting and getting time
    """

    init_schema = {
            "description": "setup time library"
    }

    timestamp_schema = {
        "description": "get seconds since epoch"
    }

    timestampms_schema = {
        "description": "get ms since epoch"
    }

    timestring_to_timestampms_schema = {
        "description": "convert time string of the form 2017-12-05 11:07:23[.000000] to epoch timestamp (in ms)"
    }

    timestampms_to_timestring_schema = {
        "description": "convert epoch timestamp in ms to time string of the form 2017-12-05 11:07:23[.000000]"
    }

    datetime_schema = {
        "description": "get the current date & time as a dictionary",
    }

    def init(self):
        pass
    
    def timestampms(self):
        return int(time.time()*1000)
        
    def timestamp(self):
        return int(time.time())
    
    def timestampms_to_timestring(self, timestampms):
        timestamp = timestampms/1000.0
        dt = datetime.fromtimestamp(timestamp)
        res = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        return res
        
        
    def timestring_to_timestampms(self, timestr):
        """
            Convert time of the form "2017-12-05 11:07:23[.000000]" to epoch timestamp (in ms)
        """
        try:
            if "." in timestr:
                t = time.strptime(timestr, "%Y-%m-%d %H:%M:%S.%f")
                
            else :
                t = time.strptime(timestr, "%Y-%m-%d %H:%M:%S")
            timestampms = 1000*time.mktime(t)
        except Exception as e:
            _log.warning("failed to convert: {}".format(e))
            timestampms = 0
        return timestampms

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

