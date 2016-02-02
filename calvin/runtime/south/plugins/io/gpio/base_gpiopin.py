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


class GPIOPinBase(object):

    """
    Base class for GPIO pin
    """

    def __init__(self, trigger, pin, direction, pull_up_down=None):
        pass

    def detect_edge(self, edge):
        """
        Detect falling, rising or both edges
        """

    def edge_detected(self):
        """
        True if edge has been detected
        """
        raise NotImplementedError()

    def set_state(self, state):
        """
        Set state of pin, 0/1 for state low/high
        """
        raise NotImplementedError()

    def get_state(self):
        """
        Get state of pin 0/1 for low/high
        """
        raise NotImplementedError()

    def pwm_start(self, frequency, dutycycle):
        """
        Start pwm
        """
        raise NotImplementedError()

    def pwm_set_frequency(self, frequency):
        """
        Set pwm frequency
        """
        raise NotImplementedError()

    def pwm_set_dutycycle(self, dutycycle):
        """
        Set pwm duty cycle
        """
        raise NotImplementedError()

    def pwm_stop(self):
        """
        Stop pwm
        """
        raise NotImplementedError()

    def shift_out(self, data, repeat):
        """
        Shift out data repeat number of times
        Parameters:
          data - list of tuples with state and time in microseconds
        """
        raise NotImplementedError()

    def close(self):
        """
        Clean up
        """
        raise NotImplementedError()
