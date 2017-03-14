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

from calvin.actor.actor import Actor, manage, condition

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class MQTTPublisher(Actor):
    """
    Publish all incoming messages to given broker"

    Arguments:
      host: <ip/name of of mqtt broker>,
      port: <port to use on mqtt broker>,

    Settings is a dictionary with optional arguments:

        {
          "ca-cert-file": <ca certificate file>,
          "verify-hostname": <False iff hostname in cert should not be verified>,
          "client-cert-file" : <client certificate file>,
          "client-key-file" : <client key file>,
          "username": <self explanatory>,
          "password": <self explanatory>,
          "will-topic" : <topic of mqtt will>
          "will-payload" : <payload of mqtt will>
        }

    input:
      topic : topic of message
      payload: payload of message
    """

    @manage(['host', 'port', 'settings'])
    def init(self, host, port, settings):
        self.host = host
        self.port = port
        self.settings = settings if settings else {}
        self.setup()

    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        if self.publisher:
            self.publisher.stop()
            self.publisher = None

    def will_end(self):
        if self.publisher:
            self.publisher.stop()

    def setup(self):
        self.use('calvinsys.network.mqtthandler', shorthand='mqtt')
        self.publisher = self['mqtt']
        self.publisher.start(self.host, self.port, self.settings)

    @condition(action_input=['topic', 'payload'])
    def send_message(self, topic, payload):
        self.publisher.publish(topic, payload)



    action_priority = (send_message, )
    requires = ['calvinsys.network.mqtthandler']
