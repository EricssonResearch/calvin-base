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

from calvin.actor.actor import Actor, manage, condition, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class OPCUAPoller(Actor):
    """
    An OPCUA Client. Connects to given OPCUA server and polls given node id's at given interval
    nodeids are of the form ns=<#>;s=<string>.

        {
          "Status": {
            "Doc": <human readable description of status code>,
            "Code": <status code>,
            "Name": <name of status code>
            },
          "Name": <name of variable>,
          "ServerTimestamp": <server timestamp>,
          "SourceTimestamp": <source timestamp>,
          "CalvinTimestamp": <local timestamp>
          "Value": <variable value>,
          "Type": <type of variable (or contents for compound variables)>,
          "Id": <id of variable>
        }

    Output:
        variable :
    """

    @manage(['endpoint', 'interval', 'nodeids'])
    def init(self, endpoint, interval, nodeids):
        self.endpoint = endpoint
        self.nodeids = [str(nodeid) for nodeid in nodeids]
        self.interval = interval
        self.setup()

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self['opcua'].shutdown()
        for timer in self.timers.values():
            if timer.active():
                timer.cancel()

    def setup(self):
        self.timers = {}
        self.use('calvinsys.opcua.client', shorthand='opcua')
        self['opcua'].connect(self.endpoint)
        self.use("calvinsys.events.timer", shorthand="timer")

    @stateguard(lambda self: not self.timers and self['opcua'].connected )
    @condition()
    def connected(self):
        # Connected - setup polling timers
        for nodeid in self.nodeids:
            self.timers[nodeid] = self['timer'].once(0)


    @stateguard(lambda self: self['opcua'].variable_changed)
    @condition(action_output=['variable'])
    def changed(self):
        # fetch changed variable
        variable = self['opcua'].get_first_changed()
        # set up new timer for next poll
        self.timers[variable['Id']] = self['timer'].once(self.interval)
        return (variable,)

    @stateguard(lambda self: any([t.triggered for t in self.timers.values()]))
    @condition()
    def poll(self):
        active_timers = filter(lambda (_, t): t.triggered, self.timers.items())
        for t in active_timers:
            t[1].ack()
            self['opcua'].poll(t[0])


    action_priority = (changed, poll, connected)
    requires = ['calvinsys.opcua.client', 'calvinsys.events.timer']
