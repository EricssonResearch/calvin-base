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

from calvin.runtime.south.plugins.async import gpiopin


class GPIOPin(object):

    """
    Set/get state of GPIO pin
    """

    def __init__(self, node, pin, direction, delay):
        """
        Export gpio pin and set direction and read delay
        """
        self.fd = gpiopin.GPIOPin(node.sched.trigger_loop, pin, direction, delay)

    def set_state(self, state):
        """
        Set state of pin
        """
        self.fd.set_state(state)

    def has_changed(self):
        """
        Returns True if value has changed since last call to get_state().
        """
        return self.fd.has_changed()

    def get_state(self):
        """
        Get state of pin
        Returns value read, None if no value read
        """
        return self.fd.get_state()

    def close(self):
        """
        Unexport pin
        """
        self.fd.close()


class GPIOHandler(object):
    def __init__(self, node):
        super(GPIOHandler, self).__init__()
        self.node = node

    def open(self, pin, direction, delay=0.2):
        if direction == "in" or direction == "out":
            return GPIOPin(self.node, pin, direction, delay)
        raise Exception("Pin direction must be in or out")

    def close(self, gpio):
        gpio.close()


def register(node, actor=None):
    """
        Called when the system object is first created.
    """
    return GPIOHandler(node)
