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
from calvin.runtime.north.plugins.port.queue.common import QueueFull, COMMIT_RESPONSE
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


class CollectBase(object):

    """
    A queue with fanin support, does not handle token order between connections
    only within a connection.
    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectBase, self).__init__()
        # Set default queue length to 4 if not specified
        length = port_properties.get('queue_length', 4)
        # Compensate length for FIFO having an unused slot
        length += 1
        # Each peer have it's own FIFO
        self.fifo = {}
        self.nbr_peers = port_properties.get('nbr_peers', 1)
        self.N = length
        # Peers ordered by id
        self.writers = []
        # NOTE: For simplicity, modulo operation is only used in fifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = {}
        self.read_pos = {}
        self.tentative_read_pos = {}
        self.tags = {}
        self.tags_are_ordering = False
        self.exhausted_tokens = {}
        self.termination = {}  # dictionary of tuples (termination type, got exhaust tokens bool)



    def __str__(self):
        fifo = "\n".join([str(k) + ": " + ", ".join(map(lambda x: str(x), self.fifo[k])) for k in self.fifo.keys()])
        return "Tokens: %s\nw:%s, r:%s, tr:%s" % (fifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self):
        state = {
            'queuetype': self._type,
            'fifo': {p: [t.encode() for t in tokens] for p, tokens in self.fifo.items()},
            'N': self.N,
            'writers': self.writers,
            'write_pos': self.write_pos,
            'read_pos': self.read_pos,
            'tentative_read_pos': self.tentative_read_pos,
            'tags': self.tags,
            'tags-are-ordering': self.tags_are_ordering
        }
        return state

    def _set_state(self, state):
        self._type = state.get('queuetype')
        self.fifo = {p: [Token.decode(t) for t in tokens] for p, tokens in state['fifo'].items()}
        self.N = state['N']
        self.writers = state['writers']
        self.write_pos = state['write_pos']
        self.read_pos = state['read_pos']
        self.tentative_read_pos = state['tentative_read_pos']
        self.tags = state.get("tags", {})
        self.tags_are_ordering = state.get("tags-are-ordering", False)

    @property
    def queue_type(self):
        return self._type

    def add_writer(self, writer, properties):
        if not isinstance(writer, basestring):
            raise Exception('Not a string: %s' % writer)
        if writer not in self.writers:
            self.read_pos[writer] = 0
            self.write_pos[writer] = 0
            self.tentative_read_pos[writer] = 0
            self.fifo.setdefault(writer, [Token(0)] * self.N)
            self.writers.append(writer)
            self.writers.sort()
        if len(self.writers) > self.nbr_peers:
            _log.debug("ADD_WRITER %s" % writer)
            self.nbr_peers = len(self.writers)

        if self.tags.get(writer, None) is None:
            self.tags[writer] = properties.get("tag", writer)

    def remove_writer(self, writer):
        if not isinstance(writer, basestring):
            raise Exception('Not a string: %s' % writer)
        _log.debug("remove_writer %s %s" % (self.reader if hasattr(self, 'reader') else "--", writer))
        del self.read_pos[writer]
        del self.tentative_read_pos[writer]
        del self.write_pos[writer]
        del self.fifo[writer]
        del self.tags[writer]
        self.writers.remove(writer)
        self.nbr_peers -= 1

    def add_reader(self, reader, properties):
        # Only used for logging
        self.reader = reader

    def remove_reader(self, reader):
        pass

    def _set_port_mapping(self, mapping):
        raise NotImplementedError
        
    def _set_port_order(self, ordering):
        raise NotImplementedError
        
    def set_config(self, config):
        """
        Set additional config information on the port.
        The 'config' parameter is a dictionary with settings.
        """
        if 'port-mapping' in config:
            self._set_port_mapping(config['port-mapping'])
        elif 'port-order' in config:
            self._set_port_order(config['port-order'])
            
    def is_exhausting(self, peer_id=None):
        if peer_id is None:
            return bool(self.termination)
        else:
            return peer_id in self.termination

    def exhaust(self, peer_id, terminate):
        # We can't do anything until we consumed the last token
        self.termination[peer_id] = (terminate, False)
        _log.debug("exhaust %s %s %s" % (self._type, peer_id, DISCONNECT.reverse_mapping[terminate]))
        return []

    def any_outstanding_exhaustion_tokens(self):
        # Between having asked actor to exhaust and receiving exhaustion tokens we don't want to assume that
        # the exhaustion is done.
        return any([not t[1] for t in self.termination.values()])

    def set_exhausted_tokens(self, tokens):
        _log.debug("set_exhausted_tokens %s %s new:%s existing:%s writers:%s" % (
            self.reader if hasattr(self, 'reader') else "--", self._type, tokens, 
            self.exhausted_tokens, self.writers))
        # Extend lists of current exhaust tokens, not replace (with likely empty list).
        # This is useful when a disconnect happens from both directions or other reasons
        self.exhausted_tokens.update({k: self.exhausted_tokens.get(k, []) + v   for k, v in tokens.items()})
        for peer_id in tokens.keys():
            self.termination[peer_id] = (self.termination[peer_id][0], True)
        remove = []
        for peer_id, exhausted_tokens in self.exhausted_tokens.items():
            if peer_id not in self.writers:
                # Make sure only writers in the exhausted_tokens
                remove.append(peer_id)
                continue
            if self._transfer_exhaust_tokens(peer_id, exhausted_tokens):
                remove.append(peer_id)
        for peer_id in remove:
            _log.debug("set_exhausted_tokens remove %s %s" % (peer_id, self.exhausted_tokens[peer_id]))
            del self.exhausted_tokens[peer_id]
        # Remove any terminated queues if empty
        for peer_id in tokens.keys():
            if peer_id not in self.writers:
                continue
            if (self.write_pos[peer_id] == self.read_pos[peer_id] and
                self.termination[peer_id][0] in [DISCONNECT.EXHAUST_PEER_RECV, DISCONNECT.EXHAUST_INPORT]):
                self.remove_writer(peer_id)
                del self.termination[peer_id]
        #fifos={w: [f[i%self.N] for i in range(self.tentative_read_pos[w], self.write_pos[w])] 
        #        for w, f in self.fifo.items()}
        #_log.debug("set_exhausted_tokens2 %s %s left:%s queue: %s" %
        #           (self.reader if hasattr(self, 'reader') else "--", self._type, self.exhausted_tokens, fifos))
        return self.nbr_peers

    def _transfer_exhaust_tokens(self, peer_id, exhausted_tokens):
        # exhausted tokens are in sequence order, but could contain tokens already in queue
        for pos, token in exhausted_tokens[:]:
            if not self.slots_available(1, peer_id):
                break
            r = self.com_write(token, peer_id, pos)
            _log.debug("write exhausted tokens on %s, %s: (%d, %s) %s" % (
                peer_id, self.reader if hasattr(self, 'reader') else "--", pos, str(token), COMMIT_RESPONSE.reverse_mapping[r]))
            # This is a token that now is in the queue, was in the queue or is invalid, for all cases remove it
            exhausted_tokens.pop(0)
        return not bool(exhausted_tokens)

    def get_peers(self):
        return self.writers

    def write(self, data, metadata):
        if not self.slots_available(1, metadata):
            raise QueueFull()
        # Write token in peer's FIFO
        write_pos = self.write_pos[metadata]
        self.fifo[metadata][write_pos % self.N] = data
        self.write_pos[metadata] = write_pos + 1
        return True

    def slots_available(self, length, metadata):
        if metadata not in self.writers:
            raise Exception("No writer %s in %s" % (metadata, self.writers))
        return length < self.N and (self.write_pos[metadata] - self.read_pos[metadata]) < (self.N - length)

    def tokens_available(self, length, metadata):
        raise NotImplementedError("Sub-class must override")

    #
    # Reading is done tentatively until committed
    # The commit and cancel are only used in action firings not communication.
    # It is always all peeked tokens that are commited or canceled.
    #
    def peek(self, metadata):
        raise NotImplementedError("Sub-class must override")

    def commit(self, metadata):
        for writer in self.writers:
            self.read_pos[writer] = self.tentative_read_pos[writer]
        # Transfer in exhausted tokens when possible
        remove = []
        #_log.debug("commit collect exhausted_tokens %s" % self.exhausted_tokens)
        for peer_id, exhausted_tokens in self.exhausted_tokens.items():
            if self._transfer_exhaust_tokens(peer_id, exhausted_tokens):
                remove.append(peer_id)
        for peer_id in remove:
            del self.exhausted_tokens[peer_id]
        # When a terminated queue is fully consumed remove it
        remove = []
        for peer_id, termination in self.termination.items():
            if (self.write_pos[peer_id] == self.read_pos[peer_id] and
                termination[0] in [DISCONNECT.EXHAUST_PEER_RECV, DISCONNECT.EXHAUST_INPORT] and
                termination[1]):
                remove.append(peer_id)
        for peer_id in remove:
            #_log.debug("commit remove")
            self.remove_writer(peer_id)
            del self.termination[peer_id]
        return bool(remove)

    def cancel(self, metadata):
        for writer in self.writers:
            self.tentative_read_pos[writer] = self.read_pos[writer]

    #
    # Queue operations used by communication which utilize a sequence number
    #

    def com_write(self, data, metadata, sequence_nbr):
        write_pos = self.write_pos[metadata]
        if sequence_nbr == write_pos:
            self.write(data, metadata)
            return COMMIT_RESPONSE.handled
        elif sequence_nbr < write_pos:
            return COMMIT_RESPONSE.unhandled
        else:
            return COMMIT_RESPONSE.invalid

    def com_peek(self, metadata):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

    def com_commit(self, reader, sequence_nbr):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

    def com_cancel(self, reader, sequence_nbr):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

    def com_is_committed(self, reader):
        raise NotImplementedError("The unordered fanin queue should not be used on an outport")

