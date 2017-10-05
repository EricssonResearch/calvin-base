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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys


class TriggeredRelativeHumidity(Actor):

    """
    Read Relative Humidity when told to.

    Inputs:
        measure: Triggers a temperature reading
    Outputs:
        percent: The measured humidity in percent
    """

    @manage([])
    def init(self):
        self.relhum = None
        self.setup()

    def setup(self):
        self.relhum = calvinsys.open(self, 'io.humidity')

    def did_migrate(self):
        self.setup()

    def will_end(self):
        calvinsys.close(self.relhum)

    @stateguard(lambda self: calvinsys.can_write(self.relhum))
    @condition(['measure'], [])
    def measure(self, _):
        calvinsys.write(self.relhum, True)

    @stateguard(lambda self: calvinsys.can_read(self.relhum))
    @condition([], ['percent'])
    def deliver(self):
        humidity = calvinsys.read(self.relhum)
        return (humidity,)

    action_priority = (deliver, measure,)
    requires = ['io.humidity']


    test_calvinsys = {'io.humidity': {'read': [50, 40],
                                      'write': [True, True]}}
    test_set = [
        {
            'inports': {'measure': [True, "True"]},
            'outports': {'percent': [50, 40]}
        }
    ]
