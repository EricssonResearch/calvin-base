# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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


from calvin.runtime.south.plugins.io.mqtt import mqtt
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class ClientHandler(object):
    _clients = {}
    
    def get(self, host, port):
        client_id = "%s:%d" % (host, port)
        if not self._clients.get(client_id, None):
            self._clients[client_id] = {"cnt": 0, "ref": mqtt.Client(host, port)}
        self._clients[client_id]["cnt"] += 1
        return self._clients[client_id]["ref"]
        
    def drop(self, client):
        client_id = "%s:%d" % (client.host(), client.port())
        if self._clients.get(client_id, None):
            self._clients[client_id]["cnt"] -= 1
            if self._clients[client_id]["cnt"] == 0:
                self._clients[client_id]["ref"].stop()
                del self._clients[client_id]
        else:
            _log.warning("No such client %s" % (client_id,))

mqtt_clients = ClientHandler()

class MQTTHandler(object):
    
    def __init__(self, node, actor):
        super(MQTTHandler, self).__init__()
        self._node = node
        self._actor = actor
        self._messages = []

    def start(self, host, port, settings):
        self._client = mqtt_clients.get(host, port)
        self._client.start(settings)

    def stop(self):
        mqtt_clients.drop(self._client)

    def subscribe(self, topic):
        self._client.subscribe(self, topic)

    def unsubscribe(self, topic):
        self._client.unsubscribe(self, topic)

    def new_message(self, topic, message):
        self._messages.append((topic,message))
        self._node.sched.trigger_loop(actor_ids=[self._actor])
    
    def has_message(self):
        return len(self._messages) > 0
        
    def get_message(self):
        return self._messages.pop(0)

    def publish(self, topic, message):
        self._client.publish(topic, message)


def register(node, actor):
    """
        Fetch a new handler
    """
    return MQTTHandler(node, actor)