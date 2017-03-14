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

from calvin.actor.actor import Actor, manage, condition, stateguard


class EnclosureFanSpeed(Actor):

    """
    Read fan speeds of enclosure

    Outputs:
        rpms : rpm values for fans in enclosure (as dict)
    """

    @manage(include=['fans'])
    def init(self, fans):
        if isinstance(fans, list):
            self.fans = fans
        else :
            self.fans = [fans]
        self.setup()

    def setup(self):
        self.use('calvinsys.sensors.enclosure', shorthand='enclosure')
        self['enclosure'].enable(fans=self.fans)

    def will_migrate(self):
        self['enclosure'].disable()

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self['enclosure'].has_fan_data)
    @condition([], ['rpms'])
    def measure(self):
        fandata = self['enclosure'].get_fan_data()
        self['enclosure'].ack_fan_data()
        return (fandata,)

    action_priority = (measure,)
    requires =  ['calvinsys.sensors.enclosure']


