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

from calvin.runtime.north.plugins.port.endpoint.common import Endpoint
from calvin.runtime.north.plugins.port.queue.common import QueueEmpty, QueueFull

#
# Local endpoints
#

class LocalInEndpoint(Endpoint):

    """docstring for LocalEndpoint"""

    def __init__(self, port, peer_port):
        super(LocalInEndpoint, self).__init__(port)
        self.peer_port = peer_port

    def is_connected(self):
        return True

    def attached(self):
        self.port.queue.add_reader(self.port.id)
        self._fifo_mismatch_fix()

    def _fifo_mismatch_fix(self):
        # Fix once mismatch of positions: we have tokens in the peer fifo that are duplicates of tokens transferred
        # (and ack never reached peer)
        # Need to remove in peer fifo since might already been consumed
        # FIXME this goes into queue internal attributes on the peer port!!!
        while (self.peer_port.queue.tokens_available(1, self.port.id) and
                self.port.queue.write_pos > self.peer_port.queue.read_pos[self.port.id]):
            self.peer_port.queue.peek(self.port.id)
            self.peer_port.queue.commit(self.port.id)

    def get_peer(self):
        return ('local', self.peer_port.id)


class LocalOutEndpoint(Endpoint):

    """docstring for LocalEndpoint"""

    def __init__(self, port, peer_port):
        super(LocalOutEndpoint, self).__init__(port)
        self.peer_port = peer_port
        self.peer_id = peer_port.id

    def is_connected(self):
        return True

    def attached(self):
        self.port.queue.add_reader(self.peer_id)

    def detached(self):
        # cancel any tentative reads to acked reads
        self.port.queue.cancel(self.peer_port.id)

    def get_peer(self):
        return ('local', self.peer_id)

    def use_monitor(self):
        return True

    def communicate(self, *args, **kwargs):
        sent = False
        while True:
            try:
                token = self.port.queue.peek(self.peer_id)
                self.peer_port.queue.write(token)
                self.port.queue.commit_one_read(self.peer_id)
                sent = True
            except QueueEmpty:
                # Nothing to read
                break
            except QueueFull:
                # Could not write, rollback read
                self.port.queue.commit_one_read(self.peer_id, False)
                break
        return sent
