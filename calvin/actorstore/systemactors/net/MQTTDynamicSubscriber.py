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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class MQTTDynamicSubscriber(Actor):
    """
    Subscribe to various topics using a various number of MQTT brokers

    Arguments:
    settings is a dictionary with optional arguments:
        {
            "tls": {
                "ca_certs": <ca certs>, "certfile": <certfile>, "keyfile": <keyfile>,
                "tls_version": <tls version>, "ciphers": <ciphers>
            },
            "auth": { "username": <username "password": <password> },
            "will": { "topic": <topic>, "payload": <payload> },
            "transport": <tcp or websocket>,
            "clean_session": <True|False>
        }

    Input:
        client_id : MQTT client ID
        uri : MQTT broker URI (format: schema://host:port)
        cmd : command keyword ('subscribe'|'unsubscribe')
        topic : topic to subscribe to
        qos : MQTT qos
    Output:
        message : dictionary {"topic": <topic>, "payload": <payload>, "client_id": <client id>}
    """
    CMD_SUBSCRIBE = "subscribe"
    CMD_UNSUBSCRIBE = "unsubscribe"

    @manage(['settings', 'layout'])
    def init(self, settings):
        if not settings:
            settings = {}
        self.settings = settings
        self.layout = {}
        self.setup()

    def setup(self):
        self.mqtt_dict = {}
        self.queue = []

    def will_migrate(self):
        for mqtt in self.mqtt_dict.itervalues():
            calvinsys.close(mqtt)
        self.mqtt_dict.clear()

    def did_migrate(self):
        self.setup()
        layout = self.layout
        self.layout = {}
        for client_id, client_details in layout.iteritems():
            details = dict(client_details)
            uri = details["uri"]
            for topic, qos in dict(details["topics"]).iteritems():
                self._update_topic(client_id, uri, self.CMD_SUBSCRIBE, topic, qos)

    """
    Read all available MQTT clients for messages and store them in a FIFO queue
    The reader will only read the first message in the queue.

    @note The rest of the messages are expected at the next readings
    """

    @stateguard(lambda self: self.queue or
                any(calvinsys.can_read(mqtt) for mqtt in self.mqtt_dict.itervalues()))
    @condition(action_output=['message'])
    def read_message(self):
        message = ""
        for (client_id, mqtt) in self.mqtt_dict.iteritems():
            if calvinsys.can_read(mqtt):
                message = calvinsys.read(mqtt)
                # add client id to the message
                message["client_id"] = client_id
                self.queue.append(message)
        if self.queue:
            message = self.queue.pop(0)
        return (message,)

    """
    Update MQTT subscribed topics for specific MQTT client
    """

    @condition(action_input=['client_id', 'uri', 'cmd', 'topic', 'qos'])
    def update_topic(self, client_id, uri, cmd, topic, qos):
        self._update_topic(client_id, uri, cmd, topic, qos)

    def _update_topic(self, client_id, uri, cmd, topic, qos):
        if not topic:
            _log.warning("Topic is missing!")
            return

        if not client_id in self.mqtt_dict.keys():
            self.mqtt_dict[client_id] = calvinsys.open(self, "mqtt.subscribe",
                                                       client_id=client_id,
                                                       topics=[topic],
                                                       uri=uri,
                                                       qos=qos,
                                                       **self.settings)
            if self.mqtt_dict[client_id]:
                self.layout[client_id] = {"uri": uri, "topics":{}}

        success = calvinsys.write(self.mqtt_dict[client_id],
                                  {"cmd": cmd, "topic":topic, "qos":qos})
        exist = topic in dict(self.layout[client_id]["topics"]).iterkeys()
        if success:
            if cmd == self.CMD_SUBSCRIBE and not exist:
                self.layout[client_id]["topics"][topic] = qos
            elif cmd == self.CMD_UNSUBSCRIBE:
                del self.layout[client_id]["topics"][topic]

    action_priority = (update_topic, read_message)
    requires = ['mqtt.subscribe']
