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
from calvin.utilities.calvinlogger import get_logger
import paho.mqtt.publish


_log = get_logger(__name__)


class Publish(base_calvinsys_object.BaseCalvinsysObject):
    """
    Publish data to given MQTT broker (using paho.mqtt implementation) 
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
            "topic": {
                "description": "topic to publish under - if given will be prefixed as topic for all messages",
                "type": "string"
            },
            "payload": {
                "description": "payload to publish - if given will be used as default payload for all messages",
                "type": ["string", "integer", "null", "boolean", "number"]
            }
        },
        "required": ["hostname"],
    }

    can_write_schema = {
        "description": "True if ready to publish next message",
        "type": "boolean"
    }

    write_schema = {
        "description": "Publish mqtt data",
        "type": ["number", "integer", "null", "boolean", "object", "string"],
        "properties": {
            "topic": {
                "type": "string"
            },
            "payload": {
                "type": ["number", "integer", "string", "null", "boolean"]
            },
        },
        "required": ["topic"]
    }

    def init(self, hostname, port=1883, qos=0, client_id='', will=None, auth=None, tls=None, transport='tcp', topic=None):
        def expand_specials(topic):
            import re
            matches = re.findall(r"##(\w+)##", topic)
            for match in matches:
                if match == "CALVINRTNAME":
                    m = self.calvinsys._node.node_name
                elif match == "CALVINRTID":
                    m = self.calvinsys._node.id
                topic = topic.replace("##{}##".format(match), m)
            return topic

        def on_connect(client, userdata, flags, rc):
            if rc != 0:
                _log.warning("Connection to MQTT broker {}:{} failed".format(hostname, port))
            else :
                _log.info("Connected to MQTT broker {}:{}".format(hostname, port))
                self.running = True

        def on_publish(client, userdata, mid):
            self.busy = False

        def on_disconnect(client, userdata, rc):
            _log.warning("MQTT broker {}:{} disconnected".format(hostname, port))
            

        # Config
        self.settings = {
            "hostname": hostname,
            "port": port,
            "client_id": client_id,
            "qos": qos,
            "will": will,
            "auth": auth,
            "tls": tls,
            "transport": transport
        }

        self.topic = expand_specials(topic) if topic else None

        self.data = []
        
        self.client = paho.mqtt.client.Client(client_id=client_id, transport=transport)
        self.client.on_connect = on_connect
        self.client.on_publish = on_publish
        self.client.on_disconnect = on_disconnect

        if will:
            payload = will.get("payload")
            if isinstance(payload, basestring):
                payload = payload.encode("ascii")
            topic = will.get("topic")
            if isinstance(topic, basestring):
                topic = topic.encode("ascii")
            
            self.client.will_set(topic=topic, payload=payload)
            
        if auth:
            self.client.username_pw_set(username=auth.get("username"), password=auth.get("password"))

        if tls:
            self.client.tls_set(ca_certs=tls.get("ca_certs"), certfile=tls.get("certfile"), keyfile=tls.get("keyfile"))

        self.client.connect_async(host=hostname, port=port)
        self.client.loop_start()
        self.running = False
        self.busy = False

    def can_write(self):
        return self.running and not self.busy

    def write(self, data):
        topic = None
        payload = None
        
        if isinstance(data, dict):
            payload = data.get("payload")
            topic = data.get("topic")
           
            if self.topic and topic:
                topic = "{}{}".format(self.topic, topic)
            elif self.topic :
                topic = self.topic
        else:
            payload = data
            topic = self.topic

        assert topic is not None

        self.busy = True
        self.client.publish(topic=topic, payload=payload)

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()
        self.client = None
