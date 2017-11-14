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

from calvin.runtime.south.plugins.async import threads
from calvin.utilities.calvinlogger import get_logger
from GChartWrapper import Line, VerticalBarStack, HorizontalBarStack, Meter

_log = get_logger(__name__)


class Chart():

    """
      This is a calvin wrapper around the google-chartwrapper for the Google Chart API.
      Documentation for this module is restricted to information about input arguments.

      Plese see google-chartwrapper API for further information about usage.
    """
    def __init__(self, node, actor, ctype=None, dataset=[], **kwargs):
        self._node = node
        self._actor = actor
        self._req_counter = 0
        self._requests = []

    def create_line(self):
        self._chart = Line([])

    def create_vbar(self):
        self._chart = VerticalBarStack([])

    def create_hbar(self):
        self._chart = HorizontalBarStack([])

    def create_meter(self):
        self._chart = Meter([])

    def get_chart_type(self):
        """
        returns the type set for the chart
        """
        return self._chart.get('cht', '')

    ##############################
    #       CHART PARAMETERS     #
    ##############################
    def set_chart_bar(self, bar):
        """
        bar must be a list comprised of:
        [ <bar width>,
          <space between bars>,
          <space between groups> ]
        """
        assert isinstance(bar, list), "'bar' %r must be a list" % type(bar)
        return self._chart.bar(*bar)

    def set_chart_encoding(self, arg):
        """
        arg must be one of 'simple','text', or 'extended'
        """
        return self._chart.encoding(arg)

    # Not tested on multiple datasets
    def set_chart_scale(self, scale):
        """
        scale must be a list or a list of lists comprised of:
        [ <data set 1 minimum value>,
          <data set 1 maximum value>,
          <data set n minimum value>,
          <data set n maximum value> ]

        will only work with text encoding!
        """
        assert isinstance(scale, list), "'scale' %r must be a list" % type(scale)
        for s in scale:
            if isinstance(s, list):
                self._chart.scale(*s)
            else:
                self._chart.scale(*scale)
                break

    # Not tested for series
    def set_chart_dataset(self, data, series=''):
        """
        Update the chart's dataset, can be two dimensional or contain string data
        """
        return self._chart.dataset(data, series)

    def set_chart_marker(self, marker):
        """
        Called one at a time for each dataset
        marker must be a list or a list of lists comprised of:
        [ <marker type>,
          <color>,
          <data set index>,
          <data point>,
          <size>,
          <priority> ]
        """
        assert isinstance(marker, list), "'marker' %r must be a list" % type(marker)
        for m in marker:
            if isinstance(m, list):
                self._chart.marker(*m)
            else:
                self._chart.marker(*marker)
                break

    def set_chart_margin(self, margin):
        """
        Set margins for chart area
        margin must be a list comprised of:
          <left margin>,
          <right margin>,
          <top margin>,
          <bottom margin>,
          <legend width>, - optional
          <legend height> - optional
        """
        assert isinstance(margin, list), "'margin' %r must be a list" % type(margin)
        assert len(margin) > 3, "'margin' %r must contain at least 4 arguments" % margin
        self._chart.margin(*margin)

    def set_chart_line(self, line):
        """
        Called one at a time for each dataset
        line must be a list or a list of lists comprised of:
        [ <data set n line thickness>,
          <length of line segment>,
          <length of blank segment> ]
        """
        assert isinstance(line, list), "'line' %r must be a list" % type(line)
        for l in line:
            if isinstance(l, list):
                self._chart.line(*l)
            else:
                self._chart.line(*line)
                break

    def set_chart_fill(self, fill):
        """
        fill must be a list or a list of lists comprised of:
        [ <fill type>,
          <fill style>,... ]

        fill type must be one of c,bg,a
        fill style must be one of s,lg,ls
        the rest of the args refer to the particular style
        """
        assert isinstance(fill, list), "'fill' %r must be a list" % type(fill)
        for f in fill:
            if isinstance(f, list):
                self._chart.fill(*f)
            else:
                self._chart.fill(*fill)
                break

    def set_chart_grid(self, grid):
        """
        grid must be a list comprised of:
        [ <x axis step size>,
          <y axis step size>,
          <length of line segment>,
          <length of blank segment>
          <x offset>,
          <y offset> ]
        """
        assert isinstance(grid, list), "'grid' %r must be a list" % type(grid)
        self._chart.grid(*grid)

    def set_chart_color(self, color):
        """
        For multiple datasets color needs to be provided as a list comprised of:
        [ <color 1>,
          ...
          <color n> ]
        """
        if type(color) is list:
            self._chart.color(*color)
        else:
            self._chart.color(color)

    def set_chart_type(self, chart_type):
        """
        Set the chart type, either Google API type or regular name,
        The recommendation is to use the create functions instead of setting the type.
        """
        assert isinstance(chart_type, basestring), "'chart_type' %r must be a basestring" % type(chart_type)
        self._chart.type(chart_type)

    # Not tested on multiple datasets
    def set_chart_label(self, label):
        """
        Add a simple label to your chart
        label can be provided as a list for multiple datasets
        """
        if type(label) is list:
            for l in label:
                self._chart.label(l)
        else:
            self._chart.label(label)

    # Not tested on multiple datasets, add for loop if list?
    def set_chart_legend(self, legend):
        """
        Add a legend to your chart
        legend can be provided as a list for multiple datasets
        """
        if type(legend) is list:
            self._chart.legend(*legend)
        else:
            self._chart.legend(legend)

    def set_chart_legend_pos(self, pos):
        """
        Define a position for your legend to occupy
        pos must one of 'b','t','r','l','bv','tv'
        """
        return self._chart.legend_pos(pos)

    def set_chart_title(self, title):
        """
        Add a title to your chart
        if optional style params are provided title must be provided as a list comprised of:
        [ <title>,
          <color>     - optional,
          <font size> - optional]
        """
        if type(title) is list:
            self._chart.title(*title)
        else:
            self._chart.title(title)

    def set_chart_size(self, size):
        """
        Set the size of the chart
        size must be provided as a list comprised of:
        [ <width>,
          <height> ]
        Note that google charts have a size limit of 300 000 pixels.
        """
        assert isinstance(size, list), "'size' %r must be a list" % type(size)
        assert len(size) is 2, "'size' %r must contain 2 elements, <width> and <height>" % size
        self._chart.size(*size)

    ##############################
    #       AXES PARAMETERS      #
    ##############################
    def set_axes_tick(self, tick):
        """
        Add tick marks in order of axes by width

        tick must be provided as a list comprised of:
        [ <index>,
          <length> ]
        """
        assert isinstance(tick, list), "'tick' %r must be a list" % type(tick)
        for t in tick:
            if isinstance(t, list):
                self._chart.axes.tick(*t)
            else:
                self._chart.axes.tick(*tick)
                break

    def set_axes_type(self, axes_type):
        """
        Define the type of axes you wish to use

        axes_type must be one of x,t,y,r
        """
        return self._chart.axes.type(axes_type)

    def set_axes_label(self, label):
        """
        label must be a list or a list of lists comprised of:
        [<index>,
         <label 1>,
         .
         .
         <label n>
        ]
        """
        assert isinstance(label, list), "'label' %r must be a list" % type(label)
        for l in label:
            if isinstance(l, list):
                self._remove_old_label(l[0])
                self._chart.axes.label(l[0], *l[1:])
            else:
                self._remove_old_label(label[0])
                self._chart.axes.label(label[0], *label[1:])
                break

    # Implementation of axes.label in Gchart lib only appends.
    def _remove_old_label(self, index):
        for item in self._chart.axes.data['labels']:
            if item[0] == str(index):
                self._chart.axes.data['labels'].remove(item)

    def set_axes_label_pos(self, label_pos):
        """
        label_pos must be a list or a list of lists comprised of:
        [ <label position 1>,
          ...,
          <label position n> 
        ]
        """
        assert isinstance(label_pos, list), "'label_pos' %r must be a list" % type(label_pos)
        for lp in label_pos:
            if isinstance(lp, list):
                self._chart.axes.position(*lp)
            else:
                self._chart.axes.position(*label_pos)
                break

    def set_axes_range(self, axes_range):
        """
        axes_range must be a list or a list of lists comprised of:
        [ <index>,
          <start of range>,
          <end of range>,
          <interval>
        ]
        """
        assert isinstance(axes_range, list), "'axes_range' %r must be a list" % type(axes_range)
        for r in axes_range:
            if isinstance(r, list):
                self._chart.axes.range(*r)
            else:
                self._chart.axes.range(*axes_range)
                break

    def set_axes_style(self, style):
        """
        style must be a list or a list of lists comprised of:
        [ <axis color>,
          <font size>,
          <alignment>,
          <drawing control>,
          <tick mark color>
        ]
        """
        assert isinstance(style, list), "'style' %r must be a list" % type(style)
        for s in style:
            if isinstance(s, list):
                self._chart.axes.style(*s)
            else:
                self._chart.axes.style(*style)
                break

    ##########################
    # Asynchronous functions #
    ##########################
    def _request_image(self, handle):
        result = self._chart.image()
        request = (item for item in self._requests if item["handle"] == handle).next()
        import time
        time.sleep(3)
        request["image"] = result
        self._node.sched.schedule_calvinsys(actor_id=self._actor)

    def _cb_error(self, *args, **kwargs):
        _log.error("%r: %r" % (args, kwargs))

    # Call to collect an image when image is available
    def receive_image(self, handle):
        request = (item for item in self._requests if item["handle"] == handle).next()
        self._requests.remove(request)
        return request["image"]

    # Call to reguest an image, image_available will return true when the image is ready
    def request_image(self):
        """
          The request will be handled in a separate thread,
          a handle is returned which can be used to receive
          the image when available.
        """
        self._req_counter += 1
        handle = self._req_counter
        request = {"handle": handle, "image": None}
        self._requests.append(request)

        defered = threads.defer_to_thread(self._request_image, handle)
        defered.addErrback(self._cb_error)
        return handle

    # The next image in order are ready
    def image_available(self):
        try:
            return (self._requests[0]["image"] is not None)
        except IndexError as e:
            print "ERROR, no image available: ", e
            return False

    # Any image is ready, in no particular order, use together with get_any_available_image()
    def any_image_available(self):
        for item in self._requests:
            if item["image"] is not None:
                return True
        return False

    # Use together with image_available()
    def get_any_available_image(self):
        request = (item for item in self._requests if item["image"] is not None).next()
        self._requests.remove(request)
        return request["image"]

    def start(self):
        print "start"

    def stop(self):
        print "stop"
