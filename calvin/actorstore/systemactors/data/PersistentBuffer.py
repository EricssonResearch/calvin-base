# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class PersistentBuffer(Actor):
    """
    Buffer data to file (when necessary.)
    Inputs:
      item : data to be buffered

    Outputs:
        current : list of data, current and on-line
        buffered : catching up of buffered data, list
    """

    def exception_handler(self, action, args):
        # Drop any incoming exceptions
        return action(self, None)

    @manage(["timer", "mem_buffer", "fifo", "buffer_name", "received", "sent", "interval", "chunk_size"])
    def init(self, buffer_id, chunk_size, interval):
        self.chunk_size = chunk_size
        self.buffer_id = buffer_id
        self.interval = interval
        self.mem_buffer = []
        self.received = 0
        self.sent = 0
        self.timer = calvinsys.open(self, "sys.timer.repeating", period=10)
        self.fifo = calvinsys.open(self, 'buffer.persistent', buffer_id=self.buffer_id, reporting=10)

    def will_end(self):
        if self.mem_buffer:
            calvinsys.write(self.fifo, self.mem_buffer)
        calvinsys.close(self.fifo)

    @stateguard(lambda self: calvinsys.can_read(self.timer))
    @condition([], [])
    def logger(self):
        calvinsys.read(self.timer)
        _log.info("{}: received: {}, sent: {}".format(self.buffer_id, self.received, self.sent))
        calvinsys.write(self.timer, self.interval)

    @condition(['item'], [])
    def receive(self, item):
        self.received += 1
        self.mem_buffer.append(item)

    @stateguard(lambda self: len(self.mem_buffer) > 0)
    @condition([], ["current"])
    def passthrough(self):
        mem_buffer = self.mem_buffer
        self.mem_buffer = []
        self.sent += len(mem_buffer)
        return (mem_buffer,)

    @stateguard(lambda self:len(self.mem_buffer) > self.chunk_size and calvinsys.can_write(self.fifo))
    @condition([], [])
    def push_data(self):
        mem_buffer = self.mem_buffer
        self.mem_buffer = []
        _log.info("pushing")
        calvinsys.write(self.fifo, mem_buffer)

    @stateguard(lambda self: calvinsys.can_read(self.fifo))
    @condition([], ['buffered'])
    def pop_data(self):
        data = calvinsys.read(self.fifo)
        self.sent += len(data)
        _log.info("popping")
        return (data, )

    action_priority = (logger, receive, passthrough, push_data, pop_data)

    requires = ['buffer.persistent', 'json', 'sys.timer.once']
