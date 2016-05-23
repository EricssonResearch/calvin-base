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

from opcua import Server
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class OPCServer(object):
    
    def __init__(self, settings):
        super(OPCServer, self).__init__()
        server_settings = settings.get("server")
        objects = settings.get("objects")
        
        self._endpoint = server_settings["endpoint"]
        self._name = server_settings["name"]
        self._namespace = server_settings["namespace"]
    
        self._init_server()
        
        
        for o in objects:
            self._add_object(o["name"])
            for variable, value in o["ro_variables"].items():
                self._add_variable(o["name"], variable, value)
            for variable, value in o["rw_variables"].items():
                self._add_variable(o["name"], variable, value, True)
        
    def start(self):
        if self._server:
            self._server.start()

    def _init_server(self):
        self._server = Server()
        self._server.set_endpoint(self._endpoint)
        self._server.set_server_name(self._name)
        self._index = self._server.register_namespace(self._namespace)
        
        _log.info("Index: %r" % (self._index,))
        self._objects_node = self._server.get_objects_node()
        _log.info("Node: %r" % (self._objects_node))
        self._objects = {}
        _log.info("Endpoints: %r" % (self._server.get_endpoints()))
        
    def stop(self):
        self._server.stop()
        
    def _add_object(self, object_name):
        self._objects[object_name] = { 'object': self._objects_node.add_object(self._index, object_name), 'variables' : {}}
        
    def _add_variable(self, object_name, variable_name, value, writable=False):
        obj = self._objects.get(object_name, None)
        if obj.get('object', None):
            var = self._objects_node.add_variable(self._index, variable_name, str(value))
            obj['variables'][variable_name] = var
            if writable:
                var.set_writable()
            return True
        return False
        
    def _get_variable(self, object_name, variable_name):
        obj = self._objects.get(object_name)
        if obj.get('object', None):
            var = obj['variables'].get(variable_name, None)
            return var
        return None
                        
    def set_value(self, object_name, variable_name, value):
        var = self._get_variable(object_name, variable_name)
        if var:
            var.set_value(str(value))
            return True
        return False
            
    def get_value(self, object_name, variable_name):
        var = self._get_variable(object_name, variable_name)
        if var:
            return var.get_value()
        return None
    