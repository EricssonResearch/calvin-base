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
from calvin.runtime.south.plugins.async import async
from paho.mqtt import client
from paho.mqtt.client import topic_matches_sub, connack_string, error_string
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

def stringify(thing):
    if isinstance(thing, unicode):
        return str(thing)
    else:
        return thing

class Client(base_mqtt.BaseClient):
    INIT = 0
    CONNECTING = 1
    CONNECTED = 2
    STOPPING = 3
    STOPPED = 4
    
    def __init__(self, host, port):
        super(Client, self).__init__(host, port)
        self._client = client.Client()
        
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe
        self._client._on_log = self._on_log
        self._state = self.INIT
        self._retry = None
        self._subscriptions = {}

    def start(self, settings):
        if self._state == self.INIT:

            ca_cert = settings.get("ca-cert-file")
            if ca_cert:
                verify_hostname = settings.get("verify-hostname")
            
            client_cert = settings.get("client-cert-file")
            client_key = settings.get("client-key-file")
            username = settings.get("username")
            username = stringify(username)
        
            if username:
                password = settings.get("password")
                password = stringify(password)
        
            verify_hostname = settings.get("verify-hostname")
            will_topic = settings.get("will-topic")
            will_topic = stringify(will_topic)
            will_payload = settings.get("will-payload")
            will_payload = stringify(will_payload)

            if ca_cert:
                self._client.tls_set(ca_cert, certfile=client_cert, keyfile=client_key)
                if not verify_hostname:
                    self._client.tls_insecure_set(True)
                
            if username:
                self._client.username_pw_set(username, password=password)
            
            if will_topic:
                self._client.will_set(will_topic, will_payload)
            
            self._state = self.CONNECTING
            self._connect(delay=0)
            self._client.loop_start()
            _log.info("starting MQTT")
    
    def stop(self):
        self._state = self.STOPPING
        if self._retry:
            self._retry.cancel()
        self._client.disconnect()
    
    def publish(self, topic, payload, qos=0, retain=False):
        _log.debug("publishing")
        if self._state == self.CONNECTED:
            (status, msg_id) = self._client.publish(topic, payload, qos, retain)
            if status != 0:
                _log.warning("{} Publication error: {}".format(status, error_string(status)))
                self._state = self.CONNECTING
            else :
                _log.debug("published ok")
                
        if self._state == self.CONNECTING:
            _log.debug("publish failed, re-connecting")
            self._reconnect()

    def _on_log(self, client, userdata, level, buf):
        _log.debug("%r : (%r) %r - %r" % (client, userdata, level, buf))
        
    def _on_publish(self, client, userdata, msg_id):
        _log.debug("Message %r published" % (msg_id,))
    
    def _connect(self, delay=5):
        if self._retry is not None:
            _log.debug("retry in progress, skipping")
            return
            
        if self._state  == self.CONNECTING:
            _log.debug("reconnecting in %f" % (delay,))
            self._retry = async.DelayedCall(delay, self._client.connect_async, self._host, self._port)
            
    def _reconnect(self):
        if self._state == self.CONNECTING:
            _log.debug("Reconnecting")
            self._connect()

        
    def _on_disconnect(self, client, userdata, status):
        if self._state not in [self.STOPPING, self.STOPPED]:
            _log.warning("Unexpected disconnect: {}".format(connack_string(status)))
            self._state = self.CONNECTING
            self._reconnect()
        else :
            self._state = self.STOPPED
            self._client.loop_stop()
        
    def _on_connect(self, client, userdata, flags, status):
        self._retry = None # Clear retry
        if status != 0:
            _log.warning("Could not connect to broker: {}".format(connack_string(status)))
            self._reconnect()
        else:
            self._state = self.CONNECTED
            _log.info("Connected to broker")
            for sub_filter in self._subscriptions:
                self._client.subscribe(sub_filter)

    def subscribe(self, subscriber, sub):
        self._subscriptions.setdefault(sub, []).append(subscriber)
        _log.debug("Adding subscription")
        if self._state == self.CONNECTED:
            self._client.subscribe(sub)

    def _on_subscribe(self, client, userdata, msg_id, granted_qos):
        _log.debug("subscription %r started" % (msg_id,))
        
    def unsubscribe(self, subscriber, sub):
        subscription = self._subscriptions.get(sub)
        subscription.remove(subscriber)
        if len(subscription) == 0:
            self._client.unsubscribe(sub)

    def _on_message(self, client, userdata, message):
        _log.debug("New message: %r" % (message.topic,))
        for sub, subscribers in self._subscriptions.items():
            if topic_matches_sub(sub, message.topic):
                for subscriber in subscribers:
                    subscriber.new_message(message.topic, message.payload)
