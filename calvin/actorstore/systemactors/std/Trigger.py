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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys


class Trigger(Actor):
    """
    Pass on given _data_ every _tick_ seconds
    Outputs:
        data: given data
    """

    @manage(['timer', 'tick', 'data', 'started'])
    def init(self, tick, data):
        self.tick = tick
        self.data = data
        self.timer = None
        self.started = False
        self.setup()

    def setup(self):
        self.timer = calvinsys.open(self, "sys.timer.repeating")

    def start(self):
        calvinsys.write(self.timer, self.tick)
        self.started = True

    @stateguard(lambda self: not self.started and calvinsys.can_write(self.timer))
    @condition([], ['data'])
    def start_timer(self):
        self.start()
        return (self.data, )

    @stateguard(lambda self: calvinsys.can_read(self.timer))
    @condition([], ['data'])
    def trigger(self):
        calvinsys.read(self.timer) # Ack
        return (self.data, )

    action_priority = (start_timer, trigger)
    requires = ['sys.timer.repeating']


    test_kwargs = {'tick': 12, 'data': "data_to_forward"}
    test_calvinsys = {'sys.timer.repeating': {'read': ["dummy_data_read"],
                                              'write': [12]}}
    test_set = [
        {
            'outports': {'data': ["data_to_forward"]}
        }
    ]
