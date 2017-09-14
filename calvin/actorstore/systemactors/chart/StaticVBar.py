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


class StaticVBar(Actor):
    """
    An actor for creating vertical bar charts.

    chart_param:         Initial settings for the chart specific parameters
    dimension:           The number of accumulated values to show simultaneously
    max_req_in_progress: Max nbr of async threads for requesting chart images

    Inputs:
      values: list of values
      labels: list of labels

    Outputs:
      b64image : base64 representation of the chart. After decoding, use from_string() \
            in the image library to unpack the image.
    """

    @manage(['params', 'dimension', 'max_req_in_progress', 'labels', 'values'])
    def init(self, chart_param={}, dimension=10, max_req_in_progress=5):
        self.params = chart_param
        self.dimension = dimension
        self.max_req_in_progress = max_req_in_progress
        self.labels = self.dimension*['']
        self.values = self.dimension*[0]

        self.setup()

    def setup(self):
        self.req_in_progress = []
        self.use("calvinsys.media.image", shorthand="image")
        self.base64 = calvinlib.use('base64')
        self.use('calvinsys.charts.chart_handler', shorthand="chart")
        self.chart_api = self['chart'].create_vbar_chart(self.params)

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
    @condition(['values', 'labels'], [])
    def send_request(self, values, labels):
        self.chart_api.set_chart_dataset(values)

        self.chart_api.set_axes_label([0] + labels)

        handle = self.chart_api.request_image()
        self.req_in_progress.append(handle)
        

    action_priority = (handle_response, send_request, )

    requires = ['calvinsys.media.image', 'base64', 'calvinsys.charts.chart_handler']
