# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class OpenWeatherMap(Actor):
    """
    Fetch weather data for given city.
    
    Input:
      city : city to get
    Output:
      status: 200/404/whatever
      forecast : json with requested data
    """

    @manage()
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.request = None
        self.reset_request()
        self.use('calvinsys.network.httpclienthandler', shorthand='http')
        self.use('calvinsys.native.python-json', shorthand="json")
        self.use('calvinsys.attribute.private', shorthand="attr")
        # Requires an api key
        self.api_key = self['attr'].get("/web/openweathermap.com/appid")
        

    def reset_request(self):
        self.received_status = False
        if self.request:
            self['http'].finalize(self.request)
            self.request = None
        

    def filter_weather_data(self, data):
        result = {}
        result['city'] = data['name']
        result['country'] = data['sys']['country']
        result['weather'] = data['weather'][0]['description']
        temperature = data['main']['temp']
        temperature -= 273.15 # Centigrade
        temperature = int(10*temperature)/10.0 # One decimal
        result['temperature'] = temperature
        return result
        
    @condition(action_input=['city'])
    @guard(lambda self, _: self.api_key and self.request is None)
    def new_request(self, city):
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = [("q", city), ("appid", self.api_key)]
        header = {}
        self.request = self['http'].get(url, params, header)
        return ActionResult()

    @condition(action_output=['status'])
    @guard(lambda self: self.request and not self.received_status and self['http'].received_headers(self.request))
    def handle_headers(self):
        status = self['http'].status(self.request)
        self.received_status = status
        return ActionResult(production=(status,))

    @condition(action_output=['forecast'])
    @guard(lambda self: self.request and self.received_status == 200 and self['http'].received_body(self.request))
    def handle_body(self):
        body = self['http'].body(self.request)
        forecast = self['json'].loads(body)
        forecast = self.filter_weather_data(forecast)
        self.reset_request()
        return ActionResult(production=(forecast,))

    @condition()
    @guard(lambda self: self.request and self.received_status and self.received_status != 200)
    def handle_empty_body(self):
        self.reset_request()
        return ActionResult()

    action_priority = (handle_body, handle_empty_body, handle_headers, new_request)
    requires = ['calvinsys.network.httpclienthandler', 'calvinsys.native.python-json', "calvinsys.attribute.private"]
