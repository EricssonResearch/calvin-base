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

from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.opcua import client

_log = get_logger(__name__)


class OPCUAClient(object):
    """
        A calvinsys module for communicating with an OPCUAServer
        
        Requires endpoint, name, namespace in /opcua/server
        
        {
                'endpoint': <endpoint>,
                'name': <name>,
                'namespace': <namespace>
        }
                
        or provided using self.server_settings().
        
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
            self._client = client.OPCUAClient(self.server_settings["endpoint"])
            self._client.connect(self.server_settings["namespace"])
            self._set_state(OPCUAClient.STATE["ready"])
        except Exception as e:
            print e

    def connect(self, server_settings):
        self.server_settings = server_settings
        async.call_in_thread(self._connect)
    
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
        variable['Endpoint'] = self.server_settings['endpoint']
        return variable
    
    def _start(self):
        self._subscription = self._client.create_subscription(OPCUAClient.INTERVAL, self.add_change)
        variables = self._client.all_variables(self.server_settings["namespace"])
        for v in variables:
            try:
                self._handles.append(self._client.subscribe_change(self._subscription, v))
            except Exception as e:
                print e
        
        # self._handle = self._client.subscribe_change(self._subscription, variables)
        self._set_state(OPCUAClient.STATE["running"])

    def start(self):
        async.run_in_thread(self._start)
        
    def _stop(self):
        self._client.unsubscribe(self._subscription, self._handle)
        self._subscription = None
        self._set_state(OPCUAClient.STATE["ready"])

    def stop(self):
        if self.state == OPCUAClient.STATE["running"]:
            async.run_in_thread(self._stop)
            
    def _shutdown(self):
        if self.state == OPCUAClient.STATE["running"]:
            self._stop()
        if self.state == OPCUAClient.STATE["ready"]:
            self._disconnect()
        self._set_state(OPCUAClient.STATE["init"])
         
    def shutdown(self):
         async.call_in_thread(self._shutdown)
    
    def _startup(self):
        _log.info("connecting")
        self._connect()
        _log.info("starting")
        self._start()

    def startup(self, server_settings):
        self.server_settings = server_settings
        async.call_in_thread(self._startup)
        
def register(node, actor):
    return OPCUAClient(node, actor)
