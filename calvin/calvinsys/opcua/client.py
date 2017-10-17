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

from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.opcua import client
import time

_log = get_logger(__name__)


class OPCUAClient(object):
    """
        A calvinsys module for communicating with an OPCUAServer
    """
    
    
    STATE = {"init": 1, "ready": 2, "running": 3}
    
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        self._changed_variables = []
        self._client = None
        self._handles = []
        self._subscription = None
        self.variable_changed = False
        self.state = OPCUAClient.STATE["init"]
    
    def _trigger(self):
        self._node.sched.schedule_calvinsys(actor_id=self._actor)
        
    def _set_state(self, new_state):
        _log.info("%s -> %s" % (self.state, new_state,))
        self.state = new_state
        self._trigger()
        
    def _connected(self):
        _log.info("OPCUA client is connected")
        self._set_state(OPCUAClient.STATE(["ready"]))
        
    def connect(self, endpoint):
        self.endpoint = endpoint
        self._client = client.OPCUAClient(self.endpoint)
        self._client.connect(notify=self._connected)
    
    @property
    def connected(self):
        return self.state == OPCUAClient.STATE["ready"]
        
    def _disconnect(self):
        self._client.disconnect()
        self._client = None
        self._set_state(OPCUAClient.STATE["init"])

    def disconnect(self):
        self._client.disconnect()
        self._client = None
        self._set_State(OPCUAClient.STATE["init"])

    def add_change(self, change):
        self._changed_variables.append(change)
        self.variable_changed = True
        self._trigger()

    def get_first_changed(self):
        variable = self._changed_variables.pop(0)
        if not self._changed_variables :
            self.variable_changed = False
        variable['endpoint'] = self.endpoint
        variable['calvints'] = int(1000*time.time())
        return variable
    
    def _start(self, nodeids):
        self._subscription = self._client.create_subscription(OPCUAClient.INTERVAL, self.add_change)
        self._variables = self._client.collect_variables(nodeids)
        for v in self._variables:
            try:
                self._handles.append(self._client.subscribe_change(self._subscription, v))
            except Exception as e:
                print e
        self._set_state(OPCUAClient.STATE["running"])

    def shutdown(self):
        self._client.disconnect()
        self._client = None
        self.state = OPCUAClient.STATE["init"]
        

    def start_subscription(self, endpoint, nodeids):
        if not self._client:
            self.endpoint = endpoint
            self._client = client.OPCUAClient(self.endpoint)
        self._client.subscribe(nodeids, self.add_change)


def register(node, actor):
    return OPCUAClient(node, actor)
