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
from GChartWrapper import Meter

_log = get_logger(__name__)


class MeterChart(BaseChart.BaseChart):
    """
    Calvinsys object handling Meter Charts
    """
    def init(self, chart_param):
        super(MeterChart, self).init()
        self._chart = Meter([])
        self._load_param(chart_param)

    def write(self, value):
        self.set_chart_dataset(value)
        self.set_chart_label(value)
        super(MeterChart, self).write()
