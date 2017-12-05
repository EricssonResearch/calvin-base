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

from calvin.actor.actor import Actor, manage, condition, calvinsys, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class LocationWeather(Actor):
    """
    Get current weather at selected destination, given as "city,country code", "city", or ",country code"

    Input:
      location : location to fetch weather from
    Output:
        forecast: weather at given city, or null on error
    """

    @manage([])
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self._service = calvinsys.open(self, "weather")

    def teardown(self):
        calvinsys.close(self._service)

    def will_migrate(self):
        self.teardown()

    def will_end(self):
        self.teardown()

    @stateguard(lambda self: self._service and calvinsys.can_write(self._service))
    @condition(action_input=['location'])
    def start_forecast(self, location):
        calvinsys.write(self._service, location)

    @stateguard(lambda self: self._service and calvinsys.can_read(self._service))
    @condition(action_output=['forecast'])
    def finish_forecast(self):
        forecast = calvinsys.read(self._service)
        return (forecast,)

    action_priority = (start_forecast, finish_forecast,)
    requires = ['weather']


    test_calvinsys = {'weather': {'read': ["sunny"],
                                  'write': ["Lund"]}}
    test_set = [
        {
            'inports': {'location': ["Lund"]},
            'outports': {'forecast': ["sunny"]}
        }
    ]
