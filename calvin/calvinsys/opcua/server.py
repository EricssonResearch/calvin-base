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

from calvin.runtime.south.plugins.opcua import server
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


class OPCServer(object):
    """
        A calvinsys module for communicating with an OPCServer
        
        Requires endpoint, name, namespace in /opcua/server
        
        {
                'endpoint': <endpoint>,
                'name': <name>,
                'namespace': <namespace>
        }
        
        as well as object descriptions in /opcua/objects.
        
        or provided using self.server_settings().
        
    """
    
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        
        self._running = False
        server_settings = self._node.attributes.get_private("/opcua")
        if server_settings:
            self._opcserver = server.OPCServer(server_settings)
        else :
            _log.warning("Expected OPCUA server settings /opcua not found")
            self._opcserver = None
            
    def server_settings(self, server_settings):
        if not self._opcserver:
            self._opcserver = server.OPCServer(server_settings)
            success = True
        else :
            _log.warning("Credentials already supplied - ignoring")
            success = False
        return success
        
    def start(self):
        if self._opcserver:
            self._opcserver.start()
            self._running = True
        else:
            _log.warning("Cannot start OPC server - no settings provided")
            
    def stop(self):
        if self._running:
            self._opcserver.stop()
        else :
            _log.warning("Cannot stop OPC server - not running")
        
    def set_value(self, object_name, variable_name, value):
        if self._running:
            self._opcserver.set_value(object_name, variable_name, value)
        
    def get_value(self, object_name, variable_name):
        if self._running:
            return self._opcserver.get_value(object_name, variable_name)

def register(node, actor):
    return OPCServer(node, actor)
