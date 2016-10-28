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

from calvin.runtime.south.plugins.io.mqtt import base_mqtt
from paho.mqtt import publish
from paho.mqtt import client
from paho.mqtt.client import topic_matches_sub, connack_string, error_string
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class Publisher(base_mqtt.BasePublisher):
    def __init__(self, topic, host, port=1883):
        super(Publisher, self).__init__(topic, host, port)
        
    def publish(self, message):
        publish.single(self._topic, message, hostname=self._host, port=self._port)

class Client(base_mqtt.BaseClient):
    def __init__(self, host, port=1883):
        super(Client, self).__init__(host, port)
        self._client = client.Client()
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe
        self._connected = False
        self._subscriptions = {}

    def host(self):
        return self._host
    
    def port(self):
        return self._port

    def start(self):
        if not self._connected:
            self._client.connect_async(self._host, self._port)
            self._client.loop_start()
            _log.debug("Starting MQTT")
    
    def stop(self):
        self._connected = False
        self._client.disconnect()
    
    def publish(self, topic, payload, qos=0, retain=False):
        if self._connected:
            (status, msg_id) = self._client.publish(topic, payload, qos, retain)
            if status != 0:
                _log.warning("{} Publication error: {}".format(topic, error_string(status)))
        else :
            _log.warning("not connected, cannot publish")

    def _on_publish(self, client, userdata, msg_id):
        _log.debug("Message %r published" % (msg_id,))
        
    def _on_disconnect(self, client, userdata, status):
        if not self._connected:
            _log.debug("Disconnected, stopping")
        if status != 0:
            _log.warning("Unexpected disconnect: {}".format(connack_string(status)))
        self._client.loop_stop()
        
    def _on_connect(self, client, userdata, flags, status):
        if status != 0:
            _log.warning("Could not connect to broker: {}".format(connack_string(status)))
        else:
            self._connected = True
            _log.debug("Connected to broker")
            for sub_filter in self._subscriptions:
                self._client.subscribe(sub_filter)

    def subscribe(self, subscriber, sub):
        self._subscriptions.setdefault(sub, []).append(subscriber)
        _log.debug("Adding subscription")
        if self._connected:
            self._client.subscribe(sub)

    def _on_subscribe(self, client, userdata, msg_id, granted_qos):
        _log.debug("subscription %r started" % (msg_id,))
        
    def unsubscribe(self, subscriber, sub):
        subscription = self._subscriptions.get(sub)
        subscription.pop(subscriber)
        if len(subscription) == 0:
            self._client.unsubscribe(sub)

    def _on_message(self, client, userdata, message):
        for sub, subscribers in self._subscriptions.items():
            if topic_matches_sub(sub, message.topic):
                for subscriber in subscribers:
                    subscriber.new_message(message.topic, message.payload)
