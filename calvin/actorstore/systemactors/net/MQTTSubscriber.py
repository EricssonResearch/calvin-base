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

from calvin.actor.actor import Actor, manage, condition, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class MQTTSubscriber(Actor):
    """
    Subscribe to given topics (list of mqtt ), output messages on message-port

    Arguments:
      host: <ip/name of mqtt broker>,
      port: <port to use on mqtt broker>,
      topics: <list of topics to subscribe to>

    settings is a dictionary with optional arguments :

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

    output:
      message : dictionary {"topic": <topic>, "payload": <payload>}
    """

    @manage(['host', 'port', 'topics', 'settings', 'message'])
    def init(self, host, port, topics, settings):
        self.host = host
        self.port = port
        self.topics = topics
        self.settings = settings if settings else {}
        self.message = None
        self.setup()

    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        if self.subscriber:
            self.subscriber.stop()
            self.subscriber = None

    def will_end(self):
        if self.subscriber:
            for topic in self.topics:
                self.subscriber.unsubscribe(topic)
            self.subscriber.stop()

    def setup(self):
        self.use('calvinsys.network.mqtthandler', shorthand='mqtt')
        self.subscriber = self['mqtt']
        self.subscriber.start(self.host, self.port, self.settings)
        for topic in self.topics:
            self.subscriber.subscribe(topic)

    @stateguard(lambda self: self.subscriber.has_message())
    @condition()
    def consume_message(self):
        topic, msg = self.subscriber.get_message()
        self.message = {"topic": topic, "payload": msg}


    @stateguard(lambda self: self.message is not None)
    @condition(action_output=['message'])
    def deliver_message(self):
        message = self.message
        self.message = None
        return (message,)


    action_priority = (deliver_message, consume_message, )
    requires = ['calvinsys.network.mqtthandler']
