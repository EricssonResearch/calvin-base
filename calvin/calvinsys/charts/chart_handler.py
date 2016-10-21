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

from calvin.runtime.south.plugins.charts import chart

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


class ChartHandler(object):
    """
    Chart handler

    To initiate a chart a dict with chart parameters must be provided
    See the README file for instructions of how to use this module.
    """

    def __init__(self, node, actor):
        self.node = node
        self.actor = actor
        self.chart = chart.Chart(node, actor)

    def create_line_chart(self, chart_param):
        self.chart.create_line()
        self._load_param(chart_param)
        return self.chart

    def create_vbar_chart(self, chart_param):
        self.chart.create_vbar()
        self._load_param(chart_param)
        return self.chart

    def create_hbar_chart(self, chart_param):
        self.chart.create_hbar()
        self._load_param(chart_param)
        return self.chart

    def create_meter_chart(self, chart_param):
        self.chart.create_meter()
        self._load_param(chart_param)
        return self.chart

    def _load_param(self, chart_param):
        chart_bar = chart_param.get('chart_bar', None)
        chart_encoding = chart_param.get('chart_encoding', None)
        chart_output_encoding = chart_param.get('chart_output_encoding', None)
        chart_scale = chart_param.get('chart_scale', None)
        chart_marker = chart_param.get('chart_marker', None)
        chart_margin = chart_param.get('chart_margin', None)
        chart_line = chart_param.get('chart_line', None)
        chart_fill = chart_param.get('chart_fill', None)
        chart_grid = chart_param.get('chart_grid', None)
        chart_color = chart_param.get('chart_color', None)
        chart_type = chart_param.get('chart_type', None)
        chart_label = chart_param.get('chart_label', None)
        chart_legend = chart_param.get('chart_legend', None)
        chart_legend_pos = chart_param.get('chart_legend_pos', None)
        chart_title = chart_param.get('chart_title', None)
        chart_size = chart_param.get('chart_size', None)

        axes_tick = chart_param.get('axes_tick', None)
        axes_type = chart_param.get('axes_type', None)
        axes_label = chart_param.get('axes_label', None)
        axes_label_pos = chart_param.get('axes_label_pos', None)
        axes_range = chart_param.get('axes_range', None)
        axes_style = chart_param.get('axes_style', None)

        if chart_bar is not None:
            self.chart.set_chart_bar(chart_bar)

        if chart_encoding is not None:
            self.chart.set_chart_encoding(chart_encoding)

        if chart_output_encoding is not None:
            self.chart.set_chart_output_encoding(chart_output_encoding)

        if chart_scale is not None:
            self.chart.set_chart_scale(chart_scale)

        if chart_marker is not None:
            self.chart.set_chart_marker(chart_marker)

        if chart_margin is not None:
            self.chart.set_chart_margin(chart_margin)

        if chart_line is not None:
            self.chart.set_chart_line(chart_line)

        if chart_fill is not None:
            self.chart.set_chart_fill(chart_fill)

        if chart_grid is not None:
            self.chart.set_chart_grid(chart_grid)

        if chart_color is not None:
            self.chart.set_chart_color(chart_color)

        if chart_type is not None:
            self.chart.set_chart_type(chart_type)

        if chart_label is not None:
            self.chart.set_chart_label(chart_label)

        if chart_legend is not None:
            self.chart.set_chart_legend(chart_legend)

        if chart_legend_pos is not None:
            self.chart.set_chart_legend_pos(chart_legend_pos)

        if chart_title is not None:
            self.chart.set_chart_title(chart_title)

        if chart_size is not None:
            self.chart.set_chart_size(chart_size)

        if axes_tick is not None:
            self.chart.set_axes_tick(axes_tick)

        if axes_type is not None:
            self.chart.set_axes_type(axes_type)

        if axes_label is not None:
            self.chart.set_axes_label(axes_label)

        if axes_label_pos is not None:
            self.chart.set_axes_label_pos(axes_label_pos)

        if axes_range is not None:
            self.chart.set_axes_range(axes_range)

        if axes_style is not None:
            self.chart.set_axes_style(axes_style)


def register(node=None, actor=None):
    """
        Called when the system object is first created.
    """
    return ChartHandler(node, actor)
