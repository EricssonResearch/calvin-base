# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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

from calvin.runtime.north.calvin_token import Token
import time
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.north.plugins.port.queue.common import QueueEmpty, QueueFull

_log = get_logger(__name__)


class Endpoint(object):

    """docstring for Endpoint"""

    def __init__(self, port, former_peer_id=None):
        super(Endpoint, self).__init__()
        self.port = port
        self.former_peer_id = former_peer_id

    def __str__(self):
        return "%s(port_id=%s)" % (self.__class__.__name__, self.port.id)

    def is_connected(self):
        return False

    def use_monitor(self):
        return False

    def communicate(self):
        """
        Called by the runtime when it is possible to transfer data to counterpart.
        """
        raise Exception("Can't communicate on endpoint in port %s.%s with id: %s" % (
            self.port.owner.name, self.port.name, self.port.id))

    def destroy(self):
        pass

    def get_peer(self):
        return (None, self.former_peer_id)

    def attached(self):
        pass

    def detached(self):
        pass



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


#
# Remote tunnel endpoints
#


class TunnelInEndpoint(Endpoint):

    """docstring for TunnelInEndpoint"""

    def __init__(self, port, tunnel, peer_node_id, peer_port_id, trigger_loop):
        super(TunnelInEndpoint, self).__init__(port)
        self.tunnel = tunnel
        self.peer_port_id = peer_port_id
        self.peer_node_id = peer_node_id
        self.trigger_loop = trigger_loop

    def __str__(self):
        str = super(TunnelInEndpoint, self).__str__()
        return str

    def is_connected(self):
        return True

    def attached(self):
        self.port.queue.add_reader(self.port.id)

    def recv_token(self, payload):
        ok = False
        # Drop any tokens that we can't write to fifo or is out of sequence
        # FIXME uses internal attributes of queue
        if self.port.queue.slots_available(1) and self.port.queue.write_pos == payload['sequencenbr']:
            self.port.queue.write(Token.decode(payload['token']))
            self.trigger_loop()
            ok = True
        elif self.port.queue.write_pos > payload['sequencenbr']:
            # Other side resent a token we already have received (can happen after a reconnect if our previous ACK was
            # lost), just ACK
            ok = True
        reply = {
            'cmd': 'TOKEN_REPLY',
            'port_id': payload['port_id'],
            'peer_port_id': payload['peer_port_id'],
            'sequencenbr': payload['sequencenbr'],
            'value': 'ACK' if ok else 'NACK'
        }
        self.tunnel.send(reply)

    def set_peer_port_id(self, id):
        self.peer_port_id = id

    def get_peer(self):
        return (self.peer_node_id, self.peer_port_id)


class TunnelOutEndpoint(Endpoint):

    """docstring for TunnelOutEndpoint"""

    def __init__(self, port, tunnel, peer_node_id, peer_port_id, trigger_loop):
        super(TunnelOutEndpoint, self).__init__(port)
        self.tunnel = tunnel
        self.peer_id = peer_port_id
        self.peer_node_id = peer_node_id
        self.trigger_loop = trigger_loop
        # Keep track of acked tokens, only contains something post call if acks comes out of order
        self.sequencenbrs_acked = []
        self.backoff = 0.0
        self.time_cont = 0.0
        self.bulk = True

    def __str__(self):
        str = super(TunnelOutEndpoint, self).__str__()
        return str

    def is_connected(self):
        return True

    def attached(self):
        self.port.queue.add_reader(self.peer_id)

    def detached(self):
        # cancel any tentative reads to acked reads
        # Tunneled transport tokens after last continuous acked token will be resent later,
        # receiver will just ack them again if rereceived
        self.port.queue.cancel(self.peer_id)

    def reply(self, sequencenbr, status):
        _log.debug("Reply on port %s/%s/%s [%i] %s" % (self.port.owner.name, self.peer_id, self.port.name, sequencenbr, status))
        if status == 'ACK':
            self._reply_ack(sequencenbr, status)
        elif status == 'NACK':
            self._reply_nack(sequencenbr, status)
        else:
            # FIXME implement ABORT
            pass

    def _reply_ack(self, sequencenbr, status):
        # FIXME uses internal queue attributes
        sequencenbr_sent = self.port.queue.tentative_read_pos[self.peer_id]
        sequencenbr_acked = self.port.queue.read_pos[self.peer_id]
        # Back to full send speed directly
        self.bulk = True
        self.backoff = 0.0
        if sequencenbr < sequencenbr_sent:
            self.sequencenbrs_acked.append(sequencenbr)
        while any(n == sequencenbr_acked for n in self.sequencenbrs_acked):
            self.port.queue.commit_one_read(self.peer_id, True)
            self.sequencenbrs_acked.remove(sequencenbr_acked)
        # Maybe someone can fill the queue again
        self.trigger_loop()

    def _reply_nack(self, sequencenbr, status):
        # FIXME uses internal queue attributes
        sequencenbr_sent = self.port.queue.tentative_read_pos[self.peer_id]
        sequencenbr_acked = self.port.queue.read_pos[self.peer_id]
        # Make send only send one token at a time and have increasing time between them
        curr_time = time.time()
        if self.bulk:
            self.time_cont = curr_time
        if self.time_cont <= curr_time:
            # Need to trigger again due to either too late NACK or switched from series of ACK
            self.trigger_loop()
        self.bulk = False
        self.backoff = min(1.0, 0.1 if self.backoff < 0.1 else self.backoff * 2.0)

        if sequencenbr < sequencenbr_sent and sequencenbr >= sequencenbr_acked:
            # Filter out ACK for later seq nbrs, should not happen but precaution
            self.sequencenbrs_acked = [n for n in self.sequencenbrs_acked if n < sequencenbr]
            # Rollback queue to the NACKed token
            while(self.port.queue.tentative_read_pos[self.peer_id] > sequencenbr):
                self.port.queue.commit_one_read(self.peer_id, False)

    def _send_one_token(self):
        token = self.port.queue.peek(self.peer_id)
        sequencenbr_sent = self.port.queue.tentative_read_pos[self.peer_id] - 1
        _log.debug("Send on port  %s/%s/%s [%i] %s" % (self.port.owner.name,
                                                       self.peer_id,
                                                       self.port.name,
                                                       sequencenbr_sent,
                                                       "" if self.bulk else "@%f/%f" % (self.time_cont, self.backoff)))
        self.tunnel.send({
            'cmd': 'TOKEN',
            'token': token.encode(),
            'peer_port_id': self.peer_id,
            'sequencenbr': sequencenbr_sent,
            'port_id': self.port.id
        })

    def use_monitor(self):
        return True

    def communicate(self, *args, **kwargs):
        # FIXME uses internal queue attributes
        sent = False
        if self.bulk:
            # Send all we have, since other side seems to keep up
            while self.port.queue.tokens_available(1, self.peer_id):
                sent = True
                self._send_one_token()
        elif (self.port.queue.tokens_available(1, self.peer_id) and
              self.port.queue.tentative_read_pos[self.peer_id] == self.port.queue.read_pos[self.peer_id] and
              time.time() >= self.time_cont):
            # Send only one since other side sent NACK likely due to their FIFO is full
            # Something to read and last (N)ACK recived
            self._send_one_token()
            sent = True
            self.time_cont = time.time() + self.backoff
            # Make sure that resend will be tried in backoff seconds
            self.trigger_loop(self.backoff)
        return sent

    def get_peer(self):
        return (self.peer_node_id, self.peer_id)
