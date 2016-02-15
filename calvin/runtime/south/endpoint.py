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

_log = get_logger(__name__)


class Endpoint(object):

    """docstring for Endpoint"""

    def __init__(self, port, former_peer_id=None):
        super(Endpoint, self).__init__()
        self.port = port
        self.former_peer_id = former_peer_id

    def __str__(self):
        return self.__class__.__name__

    def is_connected(self):
        return False

    def read_token(self):
        return None

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

#
# Local endpoints
#


class LocalInEndpoint(Endpoint):

    """docstring for LocalEndpoint"""

    def __init__(self, port, peer_port):
        super(LocalInEndpoint, self).__init__(port)
        self.peer_port = peer_port
        # When migrating from remote to local,
        # there might be initial data to read in the FIFO
        self.data_in_local_fifo = True
        self.fifo_mismatch = True

    def is_connected(self):
        return True

    def _fifo_mismatch_fix(self):
        # Fix once mismatch of positions: we have tokens in the peer fifo that are duplicates of tokens transferred
        # (and ack never reached peer)
        # Need to remove in peer fifo since might already been consumed
        while self.peer_port.fifo.can_read(self.port.id) and self.port.fifo.write_pos > self.peer_port.fifo.read_pos[self.port.id]:
            self.peer_port.fifo.read(self.port.id)
            self.peer_port.fifo.commit_reads(self.port.id, True)
        self.fifo_mismatch = False

    def _sync_local_fifos(self):
        # TODO Fix performance by only doing this at a disconnect of local port
        # Make this port's write pos to be synced with peer's read_pos as it is when using 2 FIFOs (i.e. remote)
        self.port.fifo.write_pos = self.peer_port.fifo.read_pos[self.port.id]
        # and the read pos reflect it does not actually contain any data
        self.port.fifo.read_pos[self.port.id] = self.port.fifo.write_pos
        self.port.fifo.tentative_read_pos[self.port.id] = self.port.fifo.write_pos

    def read_token(self):
        if self.fifo_mismatch:
            self._fifo_mismatch_fix()

        if self.data_in_local_fifo:
            # Empty local inport fifo once, since local transport only use outport's fifo
            token = self.port.fifo.read(self.port.id)
            if token:
                self.port.fifo.commit_reads(self.port.id, True)
                return token
            self.data_in_local_fifo = False

        token = self.peer_port.fifo.read(self.port.id)
        self.peer_port.fifo.commit_reads(self.port.id, token is not None)

        self._sync_local_fifos()
        return token

    def peek_token(self):
        if self.fifo_mismatch:
            self._fifo_mismatch_fix()

        if self.data_in_local_fifo:
            # Empty local FIFO (once) in case it contains data
            token = self.port.fifo.read(self.port.id)
            if token:
                return token

        token = self.peer_port.fifo.read(self.port.id)
        return token

    def peek_rewind(self):
        if self.data_in_local_fifo:
            self.port.fifo.rollback_reads(self.port.id)
        self.peer_port.fifo.rollback_reads(self.port.id)

    def commit_peek_as_read(self):
        if self.data_in_local_fifo:
            self.port.fifo.commit_reads(self.port.id)
            if self.port.fifo.can_read(self.port.id):
                # Still data left in own fifo, no need to commit on peer port and no sync should be done
                return
            else:
                self.data_in_local_fifo = False
        self.peer_port.fifo.commit_reads(self.port.id)
        self._sync_local_fifos()

    def available_tokens(self):
        if self.fifo_mismatch:
            self._fifo_mismatch_fix()

        tokens = 0
        if self.data_in_local_fifo:
            # Check local FIFO in case it contains data
            tokens += self.port.fifo.available_tokens(self.port.id)
            if tokens == 0:
                self.data_in_local_fifo = False
        tokens += self.peer_port.fifo.available_tokens(self.port.id)
        return tokens

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

    def get_peer(self):
        return ('local', self.peer_id)


#
# Remote endpoints
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

    def recv_token(self, payload):
        ok = False
        # Drop any tokens that we can't write to fifo or is out of sequence
        if self.port.fifo.can_write() and self.port.fifo.write_pos == payload['sequencenbr']:
            self.port.fifo.write(Token.decode(payload['token']))
            self.trigger_loop()
            ok = True
        elif self.port.fifo.write_pos > payload['sequencenbr']:
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

    def read_token(self):
        token = self.port.fifo.read(self.port.id)
        self.port.fifo.commit_reads(self.port.id, token is not None)
        return token

    def peek_token(self):
        token = self.port.fifo.read(self.port.id)
        return token

    def peek_rewind(self):
        self.port.fifo.rollback_reads(self.port.id)

    def commit_peek_as_read(self):
        self.port.fifo.commit_reads(self.port.id)

    def available_tokens(self):
        # First fit as many tokens as possible in the fifo
        return self.port.fifo.available_tokens(self.port.id)

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
        sequencenbr_sent = self.port.fifo.tentative_read_pos[self.peer_id]
        sequencenbr_acked = self.port.fifo.read_pos[self.peer_id]
        # Back to full send speed directly
        self.bulk = True
        self.backoff = 0.0
        if sequencenbr < sequencenbr_sent:
            self.sequencenbrs_acked.append(sequencenbr)
        while any(n == sequencenbr_acked for n in self.sequencenbrs_acked):
            self.port.fifo.commit_one_read(self.peer_id, True)
            self.sequencenbrs_acked.remove(sequencenbr_acked)
        # Maybe someone can fill the fifo again
        self.trigger_loop()

    def _reply_nack(self, sequencenbr, status):
        sequencenbr_sent = self.port.fifo.tentative_read_pos[self.peer_id]
        sequencenbr_acked = self.port.fifo.read_pos[self.peer_id]
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
            # Rollback fifo to the NACKed token
            while(self.port.fifo.tentative_read_pos[self.peer_id] > sequencenbr):
                self.port.fifo.commit_one_read(self.peer_id, False)

    def _send_one_token(self):
        token = self.port.fifo.read(self.peer_id)
        sequencenbr_sent = self.port.fifo.tentative_read_pos[self.peer_id] - 1
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

    def communicate(self, *args, **kwargs):
        sent = False
        if self.bulk:
            # Send all we have, since other side seems to keep up
            while self.port.fifo.can_read(self.peer_id):
                sent = True
                self._send_one_token()
        elif (self.port.fifo.can_read(self.peer_id) and
              self.port.fifo.tentative_read_pos[self.peer_id] == self.port.fifo.read_pos[self.peer_id] and
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
