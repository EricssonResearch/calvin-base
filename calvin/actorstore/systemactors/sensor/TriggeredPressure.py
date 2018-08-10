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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class TriggeredPressure(Actor):

    """
    Measure atmospheric pressure

    Inputs:
        trigger : any token triggers measurement

    Outputs:
        mbar: atmospheric pressure, in millibars
    """

    @manage(['pressure'])
    def init(self):
        self.pressure= calvinsys.open(self, "io.pressure")

    @stateguard(lambda self: calvinsys.can_read(self.pressure))
    @condition([], ['mbar'])
    def read_measurement(self):
        data = calvinsys.read(self.pressure)
        return (data,)

    @stateguard(lambda self: calvinsys.can_write(self.pressure))
    @condition(['trigger'], [])
    def trigger_measurement(self, _):
        calvinsys.write(self.pressure, True)

    action_priority = (read_measurement, trigger_measurement)
    requires = ['io.pressure']


    test_calvinsys = {'io.pressure': {'read': [20, 14],
                                      'write': [True, True]}}
    test_set = [
        {
            'inports': {'trigger': [True, "True"]},
            'outports': {'mbar': [20, 14]}
        }
    ]
