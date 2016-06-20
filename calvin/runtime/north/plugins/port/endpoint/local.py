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
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

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
                nbr, token = self.port.queue.com_peek(self.peer_id)
                self.peer_port.queue.com_write(token, nbr)
                self.port.queue.com_commit(self.peer_id, nbr)
                sent = True
            except QueueEmpty:
                # Nothing to read
                break
            except QueueFull:
                # Could not write, rollback read
                self.port.queue.com_cancel(self.peer_id, nbr)
                break
        return sent
