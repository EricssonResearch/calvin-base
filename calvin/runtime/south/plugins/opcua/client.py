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


def data_value_to_struct(data_value):
    def dt_to_ts(dt):
        import time
        import datetime
        if not dt:
            dt = datetime.datetime.now()
        try:
            res = str(time.mktime(dt.timetuple()))[:-2] + str(dt.microsecond/1000000.0)[1:]
        except Exception as e:
            _log.warning("Could not convert dt to timestamp: %r" % (e,))
            res = 0.0
        return res

    return {
        "Type": data_value.Value.VariantType.name,
        "Value": str(data_value.Value.Value),
        "Status": { "Code": data_value.StatusCode.value, 
                    "Name": data_value.StatusCode.name,
                    "Doc": data_value.StatusCode.doc
                },
        "SourceTimestamp": str(data_value.SourceTimestamp),
        "ServerTimestamp": str(data_value.ServerTimestamp)
        }


def get_node_name_and_id(node):
    # these actually connect to the remote server to fetch the data
    # so they need to run in a separate thread
    node_id = node.nodeid.to_string()
    try:
        path = node.get_path_as_string()
        node_name = "/".join([ p.split(":")[1] for p in path ])
        # node_name = node.get_display_name().to_string()
    except Exception:
        # Not all nodes have a name, use node id
        node_name = node_id
    return node_id, node_name
    
class OPCUAClient(object):
    
    class SubscriptionHandler(object):
        def __init__(self, handler):
            super(OPCUAClient.SubscriptionHandler, self).__init__()
            self._handler = handler

        def notify_handler(self, node, variable):
            node_id, node_name = get_node_name_and_id(node)
            variable["Id"] = node_id
            variable["Name"] = node_name 
            # hand the notification over to the scheduler
            self._handler(variable)

        def datachange_notification(self, node, val, data):
            async.call_in_thread(self.notify_handler, node, data_value_to_struct(data.monitored_item.Value))

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
            
    def connect(self):
        self._client = opcua.Client(self._endpoint)
        self._client.connect()
    
    def disconnect(self):
        if not self._running and self._client:
            self._client.disconnect()
            self._variables = []
            self._client = None
    
    def get_value(self, nodeid, handler):
        try:
            n = self._client.get_node(nodeid)
            s = data_value_to_struct(n.get_data_value())
            node_id, node_name = get_node_name_and_id(n)
            s["Id"] = node_id
            s["Name"] = node_name
            handler(s)
        except Exception as e:
            _log.error("get_value failed: '%s'" % (e,))

    def collect_variables(self, nodeids):
        vars = []
        for n in nodeids:
            var = None
            try:
                var = self._client.get_node(n)
            except Exception as e:
                _log.warning("Failed to get node %s: %s" % (n,e))
            vars.append(var)
        return vars
            
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
    