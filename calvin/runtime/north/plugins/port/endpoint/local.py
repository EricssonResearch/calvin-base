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

import time

from calvin.runtime.north.plugins.port.endpoint.common import Endpoint
from calvin.runtime.north.plugins.port.queue.common import QueueEmpty, QueueFull
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

#
# Local endpoints
#

PRESSURE_LENGTH = 3

class LocalInEndpoint(Endpoint):

    """docstring for LocalEndpoint"""

    def __init__(self, port, peer_port, scheduler=None):
        super(LocalInEndpoint, self).__init__(port)
        self.peer_port = peer_port
        self.peer_id = peer_port.id
        self.scheduler = scheduler
        self.pressure_count = 0
        self.pressure = [(None, 0)] * PRESSURE_LENGTH  # list with (sequence nbr, time)
        self.pressure_last = 0

    def is_connected(self):
        return True

    def attached(self):
        self.port.queue.add_reader(self.port.id, self.port.properties)
        self.port.queue.add_writer(self.peer_id, self.peer_port.properties)

    def detached(self, terminate=DISCONNECT.TEMPORARY):
        if terminate == DISCONNECT.TERMINATE:
            self.port.queue.remove_writer(self.peer_port.id)
        elif terminate == DISCONNECT.EXHAUST:
            tokens = self.port.queue.exhaust(peer_id=self.peer_port.id, terminate=DISCONNECT.EXHAUST_INPORT)
            self.remaining_tokens = {self.port.id: tokens}
        elif terminate == DISCONNECT.EXHAUST_PEER:
            tokens = self.port.queue.exhaust(peer_id=self.peer_port.id, terminate=DISCONNECT.EXHAUST_PEER_RECV)
            self.remaining_tokens = {self.port.id: tokens}

    def get_peer(self):
        return ('local', self.peer_id)


class LocalOutEndpoint(Endpoint):

    """docstring for LocalEndpoint"""

    def __init__(self, port, peer_port, scheduler=None):
        super(LocalOutEndpoint, self).__init__(port)
        self.peer_port = peer_port
        self.peer_id = peer_port.id
        self.peer_endpoint = None
        self.scheduler = scheduler

    def is_connected(self):
        return True

    def attached(self):
        self.port.queue.add_reader(self.peer_port.id, self.peer_port.properties)
        self.port.queue.add_writer(self.port.id, self.port.properties)

    def detached(self, terminate=DISCONNECT.TEMPORARY):
        if terminate == DISCONNECT.TEMPORARY:
            # cancel any tentative reads to acked reads
            self.port.queue.cancel(self.peer_port.id)
        elif terminate == DISCONNECT.TERMINATE:
            self.port.queue.cancel(self.peer_port.id)
            self.port.queue.remove_reader(self.peer_port.id)
        elif terminate == DISCONNECT.EXHAUST:
            tokens = self.port.queue.exhaust(peer_id=self.peer_port.id, terminate=DISCONNECT.EXHAUST_OUTPORT)
            self.remaining_tokens = {self.port.id: tokens}
        elif terminate == DISCONNECT.EXHAUST_PEER:
            tokens = self.port.queue.exhaust(peer_id=self.peer_port.id, terminate=DISCONNECT.EXHAUST_PEER_SEND)
            self.remaining_tokens = {self.port.id: tokens}

    def get_peer(self):
        return ('local', self.peer_id)

    def use_monitor(self):
        return True

    def communicate(self, *args, **kwargs):
        if self.peer_endpoint is None:
            for e in self.peer_port.endpoints:
                if e.peer_id == self.port.id:
                    self.peer_endpoint = e
                    break
        sent = False
        nbr = None
        while True:
            try:
                nbr, token = self.port.queue.com_peek(self.peer_id)
                self.peer_port.queue.com_write(token, self.port.id, nbr)
                self.port.queue.com_commit(self.peer_id, nbr)
                sent = True
            except QueueEmpty:
                # Nothing to read
                break
            except QueueFull:
                # Could not write, rollback read
                _log.debug("LOCAL QUEUE FULL %d %s" % (self.peer_endpoint.pressure_count, self.peer_id))
                self.port.queue.com_cancel(self.peer_id, nbr)
                if (self.peer_endpoint and
                        self.peer_endpoint.pressure[(self.peer_endpoint.pressure_count - 1) % PRESSURE_LENGTH][0] != nbr):
                    self.peer_endpoint.pressure[self.peer_endpoint.pressure_count % PRESSURE_LENGTH] = (nbr, time.time())
                    self.peer_endpoint.pressure_count += 1
                    # Inform scheduler about potential pressure event
                    if self.scheduler:
                        self.scheduler.trigger_pressure_event(self.peer_port.owner.id)
                break
        if self.peer_endpoint and nbr is not None:
            self.peer_endpoint.pressure_last = nbr
        return sent
