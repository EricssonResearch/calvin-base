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

from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.common.calvinlogger import get_logger
import paho.mqtt.subscribe
import json


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
                "type": ["number", "integer", "string", "null", "boolean", "array", "object"]
            },
        },
    }

    can_write_schema = {
        "description": "Does nothing, always return true",
        "type": "boolean"
    }

    write_schema = {
        "description": "Setup",
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
        }
    }

    def init(self, topics=None, hostname=None, port=1883, qos=0, client_id='', will=None, auth=None, tls=None, transport='tcp', payload_only=False, **kwargs):
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

        self.connected = False
        self.payload_only = payload_only
        self.topics = topics if topics else []
        self.data = []
        self.client = None

        if hostname and self.topics:
            self.setup()

    def setup(self):
        def on_connect(client, userdata, flags, rc):
            if rc != 0:
                _log.warning("Connection to MQTT broker {}:{} failed".format(hostname, port))
            else :
                _log.info("Connected to MQTT broker {}:{}".format(hostname, port))
                self.connected = True
                if self.topics:
                    topics = [(topic, self.settings["qos"]) for topic in self.topics]
                    client.subscribe(topics)

        def on_disconnect(client, userdata, rc):
            _log.warning("MQTT broker {}:{} disconnected".format(hostname, port))
            self.connected = False

        def on_message(client, userdata, message):
            payload = json.loads(message.payload.decode('utf-8'))
            self.data.append({"topic": message.topic, "payload": payload})
            self.scheduler_wakeup()

        def on_subscribe(client, userdata, message_id, granted_qos):
            _log.info("MQTT subscription {}:{} started".format(hostname, port))

        hostname = self.settings["hostname"]
        port = self.settings["port"]
        client_id = self.settings["client_id"]
        transport = self.settings["transport"]
        will = self.settings["will"]
        auth = self.settings["auth"]
        tls = self.settings["tls"]

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
        if "hostname" in data:
            self.settings["hostname"] = data["hostname"]
        if "port" in data:
            self.settings["port"] = data["port"]
        if "client_id" in data:
            self.settings["client_id"] = data["client_id"]
        if "qos" in data:
            self.settings["qos"] = data["qos"]
        if "will" in data:
            self.settings["will"] = data["will"]
        if "auth" in data:
            self.settings["auth"] = data["auth"]
        if "tls" in data:
            self.settings["tls"] = data["tls"]
        if "transport" in data:
            self.settings["tranport"] = data["transport"]
        if "payload_only" in data:
            self.settings["payload_only"] = data["payload_only"]

        if "topics" in data:
            for topic in data["topics"]:
                if topic not in self.topics:
                    self.topics.append(topic)
                    if self.connected:
                        self.client.subscribe((topic, self.settings["qos"]))

            for topic in self.topics:
                if topic not in data["topics"] and self.connected:
                    self.client.unsubscribe(topic)

            self.topics = data["topics"]

        if not self.client and self.topics and self.settings["hostname"]:
            self.setup()

    def can_read(self):
        return bool(self.data)

    def read(self):
        data = self.data.pop(0)
        if self.payload_only:
            return data.get("payload")
        else:
            return data

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()
