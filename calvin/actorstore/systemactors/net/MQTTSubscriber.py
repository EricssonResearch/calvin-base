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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class MQTTSubscriber(Actor):
    """
    Subscribe to given topics (list of mqtt ), send incoming messages to on port

    output:
      message : dictionary {"topic": <topic>, "payload": <payload>}
    """

    @manage(['host', 'port', 'topics', 'message'])
    def init(self, host, port, topics):
        self.host = host
        self.port = port
        self.topics = topics
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
            self.subscriber.stop()


    def setup(self):
        self.use('calvinsys.network.mqtthandler', shorthand='mqtt')
        self.subscriber = self['mqtt']
        self.subscriber.start(self.host, self.port)
        for topic in self.topics:
            self.subscriber.subscribe(topic)

    @condition()
    @guard(lambda self: self.subscriber.has_message())
    def consume_message(self):
        topic, msg = self.subscriber.get_message()
        self.message = {"topic": topic, "payload": msg}
        return ActionResult()

    @condition(action_output=['message'])
    @guard(lambda self: self.message is not None)
    def deliver_message(self):
        message = self.message
        self.message = None
        return ActionResult(production=(message,),)

 
    action_priority = (deliver_message, consume_message, )
    requires = ['calvinsys.network.mqtthandler']
