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

from calvin.actor.actor import Actor, manage, condition, calvinsys, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class MQTTPublisher(Actor):
    """
    Publish all incoming messages to given broker"

    Arguments:
      hostname: <ip/name of of mqtt broker>,
      port: <port to use on mqtt broker>,

    Settings is a dictionary with optional arguments.

        {
          "tls": {
              "ca_certs": <ca certs>, "certfile": <certfile>, "keyfile": <keyfile>, 
              "tls_version": <tls version>, "ciphers": <ciphers>
          },
          "auth": { "username": <username "password": <password> },
          "will": { "topic": <topic>, "payload": <payload> },
          "transport": <tcp or websocket>,
          "client_id": <id of this mqtt client>
          "topic": <prefix all outgoing message topics with this>
        }

    input:
      topic : topic of message
      payload: payload of message
    """

    @manage(['mqtt'])
    def init(self, hostname, port, settings):
        if not settings:
            settings = {}
        self.mqtt = calvinsys.open(self, "mqtt.publish", hostname=hostname, port=port, **settings)

    @stateguard(lambda actor: calvinsys.can_write(actor.mqtt))
    @condition(action_input=['topic', 'payload'])
    def send_message(self, topic, payload):
        calvinsys.write(self.mqtt, {"topic": topic, "payload": payload })

    action_priority = (send_message, )
    requires = ['mqtt.publish']

# TBD: Reenable test after updating to use new calvinsys API
#    test_kwargs = {'host': "dummy",
#                   'port': "dummy",
#                   'settings': "dummy"}
#    test_set = [
#        {
#            'inports': {'topic': [],
#                        'payload': []},
#        }
#    ]
