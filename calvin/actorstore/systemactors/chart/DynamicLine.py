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
from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib

_log = get_actor_logger(__name__)


class DynamicLine(Actor):
    """
    An actor for creating dynamic line charts.

    The chart is generating a dynamic bar chart from accumulated values and labels.

    chart_param:         Initial settings for the chart specific parameters
    dimension:           The number of accumulated values to show simultaneously
    left_to_right:       If set to false the new values will roll in from right to left
    max_req_in_progress: Max nbr of async threads for requesting chart images

    Inputs:
      label
      value

    Outputs:
      b64image : base64 representation of the chart. After decoding, use from_string() \
            in the image library to unpack the image.
    """

    @manage(['params', 'dimension', 'left_to_right', 'max_req_in_progress', 'labels', 'values'])
    def init(self, chart_param={}, dimension=10, left_to_right=False, max_req_in_progress=5):
        self.params = chart_param
        self.dimension = dimension
        self.left_to_right = left_to_right
        self.max_req_in_progress = max_req_in_progress
        self.labels = self.dimension*['']
        self.values = self.dimension*[0]

        self.setup()

    def setup(self):
        self.req_in_progress = []
        self.use("calvinsys.media.image", shorthand="image")
        self.base64 = calvinlib.use('base64')
        self.use('calvinsys.charts.chart_handler', shorthand="chart")
        self.chart_api = self['chart'].create_line_chart(self.params)

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self.req_in_progress and self.chart_api.image_available())
    @condition([], ['b64image'])
    def handle_response(self):
        handle = self.req_in_progress.pop(0)
        image = self.chart_api.receive_image(handle)
        img_str = self['image'].to_string(image, "PNG")
        result = self.base64.encode(img_str)

        return (result, )

    @stateguard(lambda self: len(self.req_in_progress) <= self.max_req_in_progress)
    @condition(['label', 'value'], [])
    def send_request(self, label, value):
        self.labels.pop(0)
        self.values.pop(0)
        self.labels.insert(self.dimension, label)
        self.values.insert(self.dimension, value)

        if self.left_to_right:
            self.chart_api.set_axes_label([0] + self.labels[::-1])
            self.chart_api.set_chart_dataset(self.values[::-1])
        else:
            self.chart_api.set_axes_label([0] + self.labels)
            self.chart_api.set_chart_dataset(self.values)

        handle = self.chart_api.request_image()
        self.req_in_progress.append(handle)
        

    action_priority = (handle_response, send_request, )

    requires = ['calvinsys.media.image', 'base64', 'calvinsys.charts.chart_handler']
