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

from calvin.utilities.calvinlogger import get_actor_logger
from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib, calvinsys

_log = get_actor_logger(__name__)


class Meter(Actor):
    """
    An actor for creating meter charts with the meter showing latest value

    chart_param: Initial settings for the chart specific parameters

    Inputs:
      value : value

    Outputs:
      b64image : base64 representation of the chart.
    """

    @manage(['_chart'])
    def init(self, chart_param={}):
        self._chart = calvinsys.open(self, 'chart.dynamic.meter', chart_param=chart_param)

        self.setup()

    def setup(self):
        self._base64 = calvinlib.use('base64')

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: calvinsys.can_read(self._chart))
    @condition([], ['b64image'])
    def handle_response(self):
        img_str = calvinsys.read(self._chart)
        result = self._base64.encode(img_str)

        return (result, )

    @stateguard(lambda self: calvinsys.can_write(self._chart))
    @condition(['value'], [])
    def send_request(self, value):
        calvinsys.write(self._chart, value)

    action_priority = (handle_response, send_request, )
    requires = ['base64', 'chart.dynamic.meter']


    test_calvinsys = {'io.chart': {'read': ["dummy"]}}
    test_set = [
        {
            'inports': {'value': []},
            'outports': {'b64image': ["ZHVtbXk="]}
        }
    ]
