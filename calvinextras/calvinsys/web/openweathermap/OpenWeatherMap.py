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
from calvin.runtime.south.plugins.async import threads
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class OpenWeatherMap(base_calvinsys_object.BaseCalvinsysObject):
    """
    OpenWeatherMap - Fetch weather data from https://www.openweathermap.com. If no location is supplied, the runtime decides.

    Location is given as "city name,ISO-3166 country code", "city name" or ",ISO-3166 country code" (note comma)
    """

    init_schema = {
        "type": "object",
        "properties": {
            "appid": {
                "description": "API key, see https://www.openweathermap.com",
                "type": "string"
            },
            "location": {
                "type": "string",
                "description": "If present, report weather for this location, given as city[,ISO-3166 country code])"
            },
            "quantity" : {
                "type": "string",
                "enum": ["temperature", "pressure", "humidity"],
                "description": "If present, restrict measurement to a single quantity"
            }
        },
        "required": ["appid"],
        "description": "Setup up api key for service"
    }

    can_write_schema = {
        "description": "Returns True if location can be selected, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Location to get weather data on, or boolean to signify 'start measurement' using configured location",
        "type": ["string", "null", "boolean"],
    }

    can_read_schema = {
        "description": "Returns True if weather data on selected location is available",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read weather data or selected quantity on location",
        "type" : ["object", "number"]
    }

    def init(self, appid, location=None, quantity=None, *args, **kwargs):
        self._api_key = appid
        self._location = location
        self._quantity = quantity
        self._in_progress = None
        self._data = None

        if not self._location:
            self._location = self._guess_location()

    def _guess_location(self):
        # no location given, check with runtime if one is set
        city = self.calvinsys._node.attributes.get_indexed_public_with_keys().get("address.locality") or ""
        country = self.calvinsys._node.attributes.get_indexed_public_with_keys().get("address.country") or "SE"
        return "{},{}".format(city, country)


    def can_write(self):
        return not bool(self._in_progress)

    def _filter_data(self, data):
        result = {}
        if self._quantity:
            if self._quantity == "temperature":
                result = data.get("main", {}).get("temp") - 273.15
            else :
                result = data.get("main", {}).get(self._quantity)
        else:
            result = {}
            result['city'] = data['name']
            result['country'] = data['sys']['country']
            result['weather'] = data['weather'][0]['description']
            result['temperature'] = int(100*(data['main']['temp'] - 273.15))/100.0
            result['humidity'] = data['main']['humidity']
            result['pressure'] = data['main']['pressure']
        return result

    def write(self, location):
        def _no_data(*args, **kwargs):
            self._data = None
            self._in_progress = None
            self.scheduler_wakeup()

        def _new_data(req, **kwargs):
            data = self._filter_data(req.json())
            self._data = data
            self._in_progress = None
            self.scheduler_wakeup()

        if location is None or isinstance(location, bool) :
            # No location given, do we already have one?
            location = self._location

        if not location :
            # no location, cannot continue from here
            return

        url = "http://api.openweathermap.org/data/2.5/weather?q={location}&appid={appid}".format(location=location, appid=self._api_key)
        self._in_progress = threads.defer_to_thread(requests.get, url)
        self._in_progress.addCallback(_new_data)
        self._in_progress.addErrback(_no_data)

    def can_read(self):
        return bool(self._data)

    def read(self):
        data = self._data
        self._data = None
        return data

    def close(self):
        del self._api_key
        if self._in_progress:
            self._in_progress.cancel()
        self._data = None
