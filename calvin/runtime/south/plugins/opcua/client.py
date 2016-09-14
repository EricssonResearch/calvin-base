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

import opcua
import logging
logging.basicConfig()

from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import async


_log = get_logger(__name__)

class OPCUAClient(object):
    
    class SubscriptionHandler(object):
        def __init__(self, handler):
            super(OPCUAClient.SubscriptionHandler, self).__init__()
            self._handler = handler
            
        def _data_value_to_struct(self, data_value):
            def dt_to_ts(dt):
                import time
                import datetime
                if not dt:
                    dt = datetime.datetime.now()
                return str(time.mktime(dt.timetuple()))[:-2] + str(dt.microsecond/1000000.0)[1:]

            return {
                "Type": data_value.Value.VariantType.name,
                "Value": str(data_value.Value.Value),
                "Status": { "Code": data_value.StatusCode.value, 
                            "Name": data_value.StatusCode.name,
                            "Doc": data_value.StatusCode.doc
                        },
                "SourceTimestamp": dt_to_ts(data_value.SourceTimestamp),
                "ServerTimestamp": dt_to_ts(data_value.ServerTimestamp)
                }
            
            
        def notify_handler(self, node, variable):
            # these actually connect to the remote server to fetch the data
            # so they need to run in a separate thread
            variable["Id"] = node.nodeid.to_string()
            variable["Name"] = node.get_display_name().to_string()
            # hand the notification over to the scheduler
            self._handler(variable)
            
        def datachange_notification(self, node, val, data):
            async.call_in_thread(self.notify_handler, node, self._data_value_to_struct(data.monitored_item.Value))
    
        def event_notification(self, event):
            _log.info("%r" % (event,))
            
    def __init__(self, endpoint):
        self._endpoint = endpoint
        self._variables = []
        self._changed_variables = []
        self._running = False
        self._client = None
        self._handle = None
        self._subscription = None
            
    def connect(self, namespace=""):
        self._client = opcua.Client(self._endpoint)
        self._client.connect()   
        _log.debug("Collecting variables from %r" % (namespace,))
        self._collect_variables(namespace)
    
    def disconnect(self):
        if not self._running and self._client:
            self._client.disconnect()
            self._variables = []
            self._client = None

    def _collect_all_variables_recur(self, node):
        _log.info("checking %s" % (node.get_display_name(),))
        children = node.get_children()
        if not children:
            return []
        variables = node.get_variables() # Not always supported
        children = [ c for c in children if c not in variables]
        result = variables
        for c in children:
            if hasattr(c, "get_children"):
                # recurse
                _log.info("Recurring for %s" % (self.get_browse_name(c),))
                result += self._collect_all_variables_recur(c)
            else:
                # Should not happen
                raise Exception("This should not happen")
        _log.info("returning from %s" % (node.get_display_name(),))
        return result
    
    def _collect_all_variables(self, namespace):
        _log.info("Fetching object node")
        objects_node = self._client.get_objects_node()
        
        # Skip server variables (for now) - unsure of generality of this
        top_level = [ c for c in objects_node.get_children() if self.get_browse_name(c).startswith(namespace) and not self.get_browse_name(c) == "0:Server"]
        result = []
        for c in top_level:
            _log.info("Collecting from %s" % (self.get_browse_name(c),))
            result += self._collect_all_variables_recur(c)
        self._variables = result
        
    def _collect_variables(self, namespace):
        objects = self._client.get_objects_node()
        folder = objects.get_child(namespace)
        self._variables = self.get_variables(folder)

    def create_subscription(self, interval, handler):
        """Create OPCUA subscription
           interval: how frequently (prob in ms) to check for changes
           handler: callback when variable changed
        """
        return self._client.create_subscription(interval, self.SubscriptionHandler(handler))
        
    def subscribe_change(self, subscription, variable):
        return subscription.subscribe_data_change(variable)
    
    def unsubscribe(self, subscription, handle):
        return subscription.unsubscribe(handle)
        
    def all_variables(self, namespace):
        if not self._variables :
            self._collect_variables(namespace)
        return self._variables

    @classmethod
    def get_variables(cls, node):
        from opcua.ua.uaprotocol_auto import NodeClass
        return node.get_children(nodeclassmask=NodeClass.Variable)
    
    @classmethod
    def get_browse_name(cls, node):
        return node.get_browse_name().to_string()

    @classmethod
    def get_display_name(cls, node):
        return node.get_display_name().to_string()
    