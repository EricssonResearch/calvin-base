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

from calvin.runtime.south.calvinsys.chart import BaseChart
from calvin.utilities.calvinlogger import get_logger
from GChartWrapper import HorizontalBarStack

_log = get_logger(__name__)


class HBarChart(BaseChart.BaseChart):
    """
    Calvinsys object handling HorizontalBarStack Charts
    """
    def init(self, chart_param, top_to_bottom):
        super(HBarChart, self).init()
        self._chart = HorizontalBarStack([])
        self._load_param(chart_param)
        self.top_to_bottom = top_to_bottom

    def write(self, data):
        labels = data['labels']
        values = data['values']

        if self.top_to_bottom:
            self.set_axes_label([2] + labels[::-1])
            self.set_chart_dataset(values[::-1])
        else:
            self.set_axes_label([2] + labels)
            self.set_chart_dataset(values)
        super(HBarChart, self).write()
