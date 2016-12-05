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

class BaseClient(object):
    """
        More or less full-featured MQTT client. Handles subscribing and publishing.
    """
    def __init__(self, host, port):
        super(BaseClient, self).__init__()
        self._host = host
        self._port = port

    def host(self):
        return self._host
        
    def port(self):
        return self._port

    def start(self):
        raise NotImplemented
    
    def stop(self):
        raise NotImplemented

    def publish(self, topic, payload, qos=0, retain=False):
        """
            topic: MQTT topic to publish
            payload: MQTT message (string, int, float, etc)
            qos: number of messages in-flight, 0 means unlimited, 1 ensures in-order delivery
            retain: True iff value can be used as 'latest good value'
        """
        raise NotImplemented

    def subscribe(self, subscriber, sub):
        """
            subscriber: object implementing 'new_message(topic, msg)' method
            sub: MQTT subscription pattern (topic1/topic2/.../topicn, with wildcards +,#)
        """
        raise NotImplemented

    def unsubscribe(self, subscriber, sub):
        """
            subscriber: object used when registering a subscription
            sub: MQTT subscription pattern (topic1/topic2/.../topicn, with wildcards +,#)
        """
        raise NotImplemented