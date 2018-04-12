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


class MQTTSubscriber(Actor):
    """
    Subscribe to given topics (list of mqtt ), output messages on message-port

    Arguments:
      hostname: <ip/name of mqtt broker>,
      port: <port to use on mqtt broker>,
      topics: <list of topics to subscribe to>

    settings is a dictionary with optional arguments :
        {
          "tls": {
              "ca_certs": <ca certs>, "certfile": <certfile>, "keyfile": <keyfile>,
              "tls_version": <tls version>, "ciphers": <ciphers>
          },
          "auth": { "username": <username "password": <password> },
          "will": { "topic": <topic>, "payload": <payload> },
          "transport": <tcp or websocket>,
          "client_id": <id of this mqtt client>
        }

    output:
      message : dictionary {"topic": <topic>, "payload": <payload>}
    """

    @manage(['mqtt'])
    def init(self, hostname, port, topics, settings):
        if not settings:
            settings = {}
        self.mqtt = calvinsys.open(self, "mqtt.subscribe", topics=topics, hostname=hostname, port=port, **settings )


    @stateguard(lambda actor: calvinsys.can_read(actor.mqtt))
    @condition([], ['message'])
    def read_message(self):
        message = calvinsys.read(self.mqtt)
        return (message,)

    action_priority = (read_message, )
    requires = ['mqtt.subscribe']


#    TBD: Reenable test after updating to use new calvinsys API
#    test_kwargs = {'host': "dummy",
#                   'port': "dummy",
#                   'topics': "dummy",
#                   'settings': "dummy"}
#    test_set = [
#        {
#            'output': {'message': []}
#        }
#    ]
