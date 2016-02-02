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

from calvin.runtime.south.plugins.io.gpio import gpiopin


class GPIOPin(object):

    """
    GPIO pin
    """

    def __init__(self, node, pin, direction, pull):
        """
        Init gpio pin
        Parameters:
          node - calvin node
          pin - gpio pin
          direction - pin direction (i=in, o=out)
          pull - pull resistor (u=up, d=down)
        """
        self.gpio = gpiopin.GPIOPin(node.sched.trigger_loop, pin, direction, pull)

    def detect_edge(self, edge):
        """
        Detect falling/rising edges, use edge_detected/edge_value to get changes
        Parameters
          edge - Edge to trigger on (r=rising, f=falling, b=both)
        """
        if edge == "f" or edge == "r" or edge == "b":
            self.gpio.detect_edge(edge)
        else:
            raise Exception("Edge must be f, r or b (falling, rising or both)")

    def edge_detected(self):
        """
        Return True if edge has been detected
        """
        return self.gpio.edge_detected()

    def edge_value(self):
        """
        Return value from last rising or falling edge
        """
        return self.gpio.edge_value()

    def set_state(self, state):
        """
        Set state of pin
        Parameters:
          state - 1/0 for high/low
        """
        self.gpio.set_state(state)

    def get_state(self):
        """
        Return state of pin, 1/0 for high/low
        """
        return self.gpio.get_state()

    def pwm_start(self, frequency, dutycycle):
        """
        Start pwm with frequency and dutycycle
        """
        self.gpio.pwm_start(frequency, dutycycle)

    def pwm_set_frequency(self, frequency):
        """
        Set pwm frequency
        """
        self.gpio.pwm_set_frequency(frequency)

    def pwm_set_dutycycle(self, dutycycle):
        """
        Set pwm duty cycle
        """
        self.gpio.pwm_set_dutycycle(dutycycle)

    def pwm_stop(self):
        """
        Stop pwm
        """
        self.gpio.pwm_stop()

    def shift_out(self, data, repeat):
        """
        Shift out data
        Parameters:
          data - list of tuples with state and time in microseconds
          repeat - number of times to repeat
        """
        self.gpio.shift_out(data, repeat)

    def close(self):
        """
        Unexport pin
        """
        self.gpio.close()


class GPIOHandler(object):

    def __init__(self, node):
        super(GPIOHandler, self).__init__()
        self.node = node

    def open(self, pin, direction, pull=None):
        if direction != "i" and direction != "o":
            raise Exception("Pin direction must be i or o (in or out)")
        if pull is not None:
            if pull != "u" and pull != "d":
                raise Exception("Pull configuration must be u or d (up or down)")
        return GPIOPin(self.node, pin, direction, pull)

    def close(self, gpio):
        gpio.close()


def register(node, actor=None):
    """
        Called when the system object is first created.
    """
    return GPIOHandler(node)
