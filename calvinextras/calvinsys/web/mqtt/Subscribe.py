# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

from calvin.runtime.south.plugins.async import threads
from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.utilities.calvinlogger import get_logger
import paho.mqtt.subscribe


_log = get_logger(__name__)


class Subscribe(base_calvinsys_object.BaseCalvinsysObject):
    """
    Subscribe to data on given MQTT broker (using paho.mqtt implementation)
    """

    init_schema = {
        "type": "object",
        "properties": {
            "hostname": {
                "description": "hostname of broker",
                "type": "string"
            },
            "port": {
                "description": "port to use, defaults to 1883",
                "type": "integer"
            },
            "qos": {
                "description": "MQTT qos, default 0",
                "type": "number"
            },
            "client_id": {
                "description": "MQTT client id to use; will be generated if not given",
                "type": "string"
            },
            "will": {
                "description": "message to send on connection lost",
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                    },
                    "payload": {
                        "type": "string"
                    },
                    "qos": {
                        "type": "string"
                    },
                    "retain": {
                        "type": "string"
                    }
                },
                "required": ["topic"]
            },
            "auth": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string"
                    },
                    "password": {
                        "type": "string"
                    }
                },
               "required": ["username"]
            },
            "tls": {
                "description": "TLS configuration for client",
                "type": "object",
                "properties": {
                    "ca_certs": {
                        "type": "string",
                    },
                    "certfile": {
                        "type": "string"
                    },
                    "keyfile": {
                        "type": "string"
                    },
                    "tls_version": {
                        "type": "string"
                    },
                    "ciphers": {
                        "type": "string"
                    }
                },
                "required": ["ca_certs"]
            },
            "transport": {
                "description": "transport to use",
                "enum": ["tcp", "websocket"]

            },
            "topics": {
                "description": "topics to subscribe to",
                "type": "array",
                "items": {
                    "type": "string",
                    "minItems": 1
                }
            },
            "payload_only": {
                "description": "only retrieve payload (not entire message)",
                "type": "boolean"
            }
        },
        "required": ["hostname", "topics"],
    }

    can_read_schema = {
        "description": "True if there is a message is available",
        "type": "boolean"
    }

    read_schema = {
        "description": "retrieve received message",
        "type": ["number", "integer", "null", "boolean", "object", "string"],
        "properties": {
            "topic": {
                "type": "string"
            },
            "payload": {
                "type": ["number", "integer", "string", "null", "boolean"]
            },
        },
    }

    can_write_schema = {
        "description": "Does nothing, always return true",
        "type": "boolean"
    }

    write_schema = {
        "description": "Does nothing"
    }

    def init(self, topics, hostname, port=1883, qos=0, client_id='', will=None, auth=None, tls=None, transport='tcp', payload_only=False, **kwargs):
        def on_connect(client, userdata, flags, rc):
            if rc != 0:
                _log.warning("Connection to MQTT broker {}:{} failed".format(hostname, port))
            else :
                _log.info("Connected to MQTT broker {}:{}".format(hostname, port))
                client.subscribe(self.topics)

        def on_disconnect(client, userdata, rc):
            _log.warning("MQTT broker {}:{} disconnected".format(hostname, port))

        def on_message(client, userdata, message):
            self.data.append({"topic": message.topic, "payload": message.payload})
            self.scheduler_wakeup()

        def on_subscribe(client, userdata, message_id, granted_qos):
            _log.info("MQTT subscription {}:{} started".format(hostname, port))

        # Config
        self.settings = {
            "msg_count": 1,
            "hostname": hostname,
            "port": port,
            "client_id": client_id,
            "qos": qos,
            "will": will,
            "auth": auth,
            "tls": tls,
            "transport": transport
        }

        _log.info("TLS: {}".format(tls))
        self.payload_only = payload_only
        self.topics = [(topic.encode("ascii"), qos) for topic in topics]
        self.data = []

        self.client = paho.mqtt.client.Client(client_id=client_id, transport=transport)
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
        self.client.on_subscribe = on_subscribe

        if will:
            # set will
            # _log.info("Setting will: {}: {}".format(will.get("topic"), will.get("payload")))
            self.client.will_set(topic=will.get("topic"), payload=will.get("payload"))

        if auth:
            # set auth
            # _log.info("setting auth: {}/{}".format(auth.get("username"), auth.get("password")))
            self.client.username_pw_set(username=auth.get("username"), password=auth.get("password"))

        if tls:
            #_log.info("setting tls: {} / {} / {}".format(tls.get("ca_certs"), tls.get("certfile"), tls.get("keyfile")))
            self.client.tls_set(ca_certs=tls.get("ca_certs"), certfile=tls.get("certfile"), keyfile=tls.get("keyfile"))


        self.client.connect_async(host=hostname, port=port)
        self.client.loop_start()


    def can_write(self):
        return True

    def write(self, data=None):
        pass

    def can_read(self):
        return bool(self.data)

    def read(self):
        data = self.data.pop(0)
        if self.payload_only:
            return data.get("payload")
        else :
            return data

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()
