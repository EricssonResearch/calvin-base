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

from calvin.runtime.south.plugins.async import async, threads
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.opcua import client
import time

_log = get_logger(__name__)


class OPCUAClient(object):
    """
        A calvinsys module for communicating with an OPCUAServer
    """
    
    INTERVAL = 100 # Interval to use in subscription check, probably ms
    
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
        self._node.sched.trigger_loop(actor_ids=[self._actor])
        
    def _set_state(self, new_state):
        _log.info("%s -> %s" % (self.state, new_state,))
        self.state = new_state
        self._trigger()
        
    def _connect(self):
        try:
            self._client = client.OPCUAClient(self.endpoint)
            self._client.connect()
            self._set_state(OPCUAClient.STATE["ready"])
        except Exception as e:
            print e

    def connect(self, endpoint):
        self.endpoint = endpoint
        async.call_in_thread(self._connect)
    
    @property
    def connected(self):
        return self.state == OPCUAClient.STATE["ready"]
        
    def _disconnect(self):
        self._client.disconnect()
        self._client = None
        self._set_state(OPCUAClient.STATE["init"])

    def disconnect(self):
        if self.state == OPCUAClient.STATE["ready"]:
            async.call_in_thread(self._disconnect)

    def add_change(self, change):
        self._changed_variables.append(change)
        self.variable_changed = True
        self._trigger()

    def get_first_changed(self):
        variable = self._changed_variables.pop(0)
        if not self._changed_variables :
            self.variable_changed = False
        variable['Endpoint'] = self.endpoint
        variable['CalvinTimestamp'] = time.time()
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
        
    def _stop(self):
        self._client.unsubscribe(self._subscription, self._handle)
        self._subscription = None
        self._set_state(OPCUAClient.STATE["ready"])

    def stop_subscription(self):
        if self.state == OPCUAClient.STATE["running"]:
            async.call_in_thread(self._stop)
            
    def _shutdown(self):
        if self.state == OPCUAClient.STATE["running"]:
            self._stop()
        if self.state == OPCUAClient.STATE["ready"]:
            self._disconnect()
        self._set_state(OPCUAClient.STATE["init"])
         
    def shutdown(self):
         async.call_in_thread(self._shutdown)

    def start_subscription(self, endpoint, nodeids):
        self.endpoint = endpoint
        threads.call_multiple_in_thread([
            (self._connect, [], {}),
            (self._start, [nodeids], {})
        ])

    def poll(self, nodeid):
        if self.state != OPCUAClient.STATE["ready"]:
            _log.warning("Cannot poll - no connection, or connection busy")
            return
        async.call_in_thread(self._client.get_value, str(nodeid), self.add_change)
        
def register(node, actor):
    return OPCUAClient(node, actor)
