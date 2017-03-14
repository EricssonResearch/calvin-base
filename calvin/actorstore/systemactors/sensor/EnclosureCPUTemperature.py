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


class EnclosureCPUTemperature(Actor):

    """
    Read CPU temperature of servers in an enclosure

    Outputs:
        temperatures : dict of the form {"server-n": temp | 1 <= n <= 16 }
    """

    @manage(["servers"])
    def init(self, servers):
        self.servers = servers
        self.setup()

    def setup(self):
        self.use('calvinsys.sensors.enclosure', shorthand='enclosure')
        self['enclosure'].enable(cpu_temps=self.servers)

    def will_migrate(self):
        self['enclosure'].disable()

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: self['enclosure'].has_cpu_temps)
    @condition([], ['temperatures'])
    def measure(self):
        data = self['enclosure'].get_cpu_temps()
        self['enclosure'].ack_cpu_temps()
        return (data,)

    action_priority = (measure,)
    requires =  ['calvinsys.sensors.enclosure']


