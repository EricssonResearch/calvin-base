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

from calvin.utilities.utils import enum

COMMIT_RESPONSE = enum('handled', 'unhandled', 'invalid')

class QueueNone(object):
    def __init__(self):
        super(QueueNone, self).__init__()
        self.state = {'queuetype': 'none'}

    def _state(self):
        return self.state

    def _set_state(self, state):
        self.state = state

    def __str__(self):
        return "QueueNone: %s" % str(self.state)

    @property
    def queue_type(self):
        return self.state["queuetype"]


class QueueEmpty(Exception):
    def __init__(self, *args, **kwargs):
        super(QueueEmpty, self).__init__(*args)
        self.reader = kwargs.get('reader', "")

    def __str__(self):
        return "Queue is empty for peer '%s' " % self.reader


class QueueFull(Exception):
    def __init__(self, *args, **kwargs):
        super(QueueFull, self).__init__(*args)

    def __str__(self):
        return "Queue is full"


