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
#import logging
#logging.basicConfig()

from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import threads, async

WATCHDOG_TIMER=10
RECONNECT_TIMER=10

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
        "type": data_value.Value.VariantType.name,
        "value": str(data_value.Value.Value),
        "status": { "code": data_value.StatusCode.value, 
                    "name": data_value.StatusCode.name,
                    "doc": data_value.StatusCode.doc
                },
        "sourcets": str(data_value.SourceTimestamp),
        "serverts": str(data_value.ServerTimestamp)
        }


def get_node_id_as_string(node):
    nodeid = str(node.nodeid)
    # nodeid is of the form (ns=X;s=XXX), remove parentheses
    nodeid = nodeid[nodeid.index('(')+1:nodeid.rindex(')')]
    return nodeid

class OPCUAClient(object):
    
    INTERVAL = 1000 # Interval to use in subscription check, probably ms
    
    class SubscriptionHandler(object):
        def __init__(self, handler, watchdog=None):
            super(OPCUAClient.SubscriptionHandler, self).__init__()
            self._handler = handler
            self._watchdog = watchdog
            self.saw_data = False
            # if available, set up watchdog to be called every 30 seconds
            if self._watchdog:
                async.DelayedCall(WATCHDOG_TIMER, self.check_data)

        def check_data(self):
            if self.saw_data:
                self.saw_data = False
                async.DelayedCall(WATCHDOG_TIMER, self.check_data)
            else:
                _log.info("No data for {} seconds".format(2*WATCHDOG_TIMER))
                self._watchdog()
            
        def notify_handler(self, node, variable):
            variable["id"] = get_node_id_as_string(node)
            # kick the watchdog
            self.saw_data = True
            # hand the notification over to the scheduler
            self._handler(variable)

        def datachange_notification(self, node, val, data):
            self.notify_handler(node, data_value_to_struct(data.monitored_item.Value))

        def event_notification(self, event):
            _log.info("%r" % (event,))
            
    def __init__(self, endpoint):
        self._endpoint = endpoint
        self.nodeids = []
        self.subscription = None
        self._changed_variables = []
        self._running = False
        self._client = None
        self._handle = None
        self._reconnect_in_progress = None
            
    def connect(self, notifier):
        self._client = opcua.Client(self._endpoint)
        d = threads.defer_to_thread(self._client.connect)
        d.addCallback(notifier)
        d.addErrback(self._retry_connect, notifier)
    
    def _retry_connect(self, failure, notifier):
        failtype = failure.type
        _log.info("Failed to connect, with reason {}, retrying in {}".format(failtype, RECONNECT_TIMER))
        if self._client:
            # Only retry if client has not been deleted (disconnected or migrated)
            self._reconnect_in_progress = async.DelayedCall(RECONNECT_TIMER, self.connect, notifier)

    def disconnect(self):
        if self.subscription:
            async.call_in_thread(self.subscription.delete)
        if self._client:
            async.call_in_thread(self._client.disconnect)
        self._client = None

    def _collect_variables(self):
        vars = []
        for n in self.nodeids:
            var = None
            try:
                var = self._client.get_node(n)
            except Exception as e:
                _log.warning("Failed to get node %s: %s" % (n,e))
            vars.append(var)
        return vars

    def _subscribe_variables(self, variables):
        for v in variables:
            self.subscription.subscribe_data_change(v)
        
    def _subscribe_changes(self, variables):
        d = threads.defer_to_thread(self._subscribe_variables, variables)
        d.addErrback(self._subscribe_error)

    def _setup_subscription(self, subscription):
        self.subscription = subscription
        d = threads.defer_to_thread(self._collect_variables)
        d.addCallback(self._subscribe_changes)
        d.addErrback(self._subscribe_error)

    def _subscribe_error(self, failure):
        _log.warning("Failed to setup subscription with reason {} - resetting connection".format(failure.type))
        async.DelayedCall(WATCHDOG_TIMER, self.watchdog)
    
    def subscribe(self, nodeids, handler):
        self.nodeids = nodeids
        self.handler = handler
        def notifier(dummy=None):
            d = threads.defer_to_thread(self._client.create_subscription, self.INTERVAL, self.SubscriptionHandler(handler, self._watchdog))
            d.addCallback(self._setup_subscription)
            d.addErrback(self._subscribe_error)
        if self._client:
            notifier()
        else :
            self.connect(notifier)

    def _watchdog(self):
        if self._client:
            _log.warning("Data watchdog triggered, resetting connection")
            self.disconnect()
            self.subscribe(self.nodeids, self.handler)
        
    def subscribe_change(self, subscription, variable):
        return subscription.subscribe_data_change(variable)
    
    def unsubscribe(self, subscription, handle):
        return subscription.unsubscribe(handle)
