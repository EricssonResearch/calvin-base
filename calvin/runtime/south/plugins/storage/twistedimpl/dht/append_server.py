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

# Methods modified from Kademlia with Copyright (c) 2014 Brian Muller:
# transferKeyValues, get_concat, _nodesFound, _handleFoundValues
# see https://github.com/bmuller/kademlia/blob/master/LICENSE

import json
import uuid
import types

from twisted.internet import defer, task, reactor
from kademlia.network import Server
from kademlia.protocol import KademliaProtocol
from kademlia.crawling import NodeSpiderCrawl, ValueSpiderCrawl, RPCFindResponse
from kademlia.utils import digest
from kademlia.storage import ForgetfulStorage
from kademlia.node import Node
from kademlia import version as kademlia_version
from collections import Counter

from twisted.python import log
from calvin.utilities import calvinlogger
import base64

_log = calvinlogger.get_logger(__name__)

# Make twisted (rpcudp) logs go to null
log.startLogging(log.NullFile(), setStdout=0)


# Fix for None types in storage
class ForgetfulStorageFix(ForgetfulStorage):
    def get(self, key, default=None):
        self.cull()
        if key in self.data:
            return (True, self[key])
        return (False, default)


class KademliaProtocolAppend(KademliaProtocol):

    def __init__(self, *args, **kwargs):
        self.set_keys = kwargs.pop('set_keys', set([]))
        KademliaProtocol.__init__(self, *args, **kwargs)

    ###############################################################################
    # TODO remove this when kademlia v0.6 available, bug fixes, see upstream Kademlia
    def handleCallResponse(self, result, node):
         """
         If we get a response, add the node to the routing table.  If
         we get no response, make sure it's removed from the routing table.
         """
         if result[0]:
             self.log.info("got response from %s, adding to router" % node)
             _log.debug("got response from %s, adding to router" % node)
             if self.router.isNewNode(node):
                 self.transferKeyValues(node)
             self.router.addContact(node)
         else:
             self.log.debug("no response from %s, removing from router" % node)
             _log.debug("no response from %s, removing from router" % node)
             self.router.removeContact(node)
         return result

    def maybeTransferKeyValues(self, node):
        if self.router.isNewNode(node):
            self.transferKeyValues(node)

    def rpc_ping(self, sender, nodeid):
        source = Node(nodeid, sender[0], sender[1])
        _log.debug("rpc_ping sender=%s, source=%s" % (sender, source))
        self.maybeTransferKeyValues(source)
        self.router.addContact(source)
        return self.sourceNode.id

    def rpc_store(self, sender, nodeid, key, value):
        source = Node(nodeid, sender[0], sender[1])
        _log.debug("rpc_store sender=%s, source=%s, key=%s, value=%s" % (sender, source, base64.b64encode(key), str(value)))
        self.maybeTransferKeyValues(source)
        self.router.addContact(source)
        self.log.debug("got a store request from %s, storing value" % str(sender))
        self.storage[key] = value
        return True

    def rpc_find_node(self, sender, nodeid, key):
        self.log.info("finding neighbors of %i in local table" % long(nodeid.encode('hex'), 16))
        source = Node(nodeid, sender[0], sender[1])
        _log.debug("rpc_find_node sender=%s, source=%s, key=%s" % (sender, source, base64.b64encode(key)))
        self.maybeTransferKeyValues(source)
        self.router.addContact(source)
        node = Node(key)
        return map(tuple, self.router.findNeighbors(node, exclude=source))
    #
    ###############################################################################

    def transferKeyValues(self, node):
        """
        Given a new node, send it all the keys/values it should be storing.

        @param node: A new node that just joined (or that we just found out
        about).

        Process:
        For each key in storage, get k closest nodes.  If newnode is closer
        than the furtherst in that list, and the node for this server
        is closer than the closest in that list, then store the key/value
        on the new node (per section 2.5 of the paper)
        """
        _log.debug("**** transfer key values %s ****" % node)
        ds = []
        for key, value in self.storage.iteritems():
            keynode = Node(digest(key))
            neighbors = self.router.findNeighbors(keynode)
            _log.debug("transfer? nbr neighbors=%d, key=%s, value=%s" % (len(neighbors), base64.b64encode(key), str(value)))
            if len(neighbors) > 0:
                newNodeClose = node.distanceTo(keynode) < neighbors[-1].distanceTo(keynode)
                thisNodeClosest = self.sourceNode.distanceTo(keynode) < neighbors[0].distanceTo(keynode)
            if len(neighbors) == 0 or (newNodeClose and thisNodeClosest):
                if key in self.set_keys:
                    _log.debug("transfer append key value key=%s, value=%s" % (base64.b64encode(key), str(value)))
                    ds.append(self.callAppend(node, key, value))
                else:
                    _log.debug("transfer store key value key=%s, value=%s" % (base64.b64encode(key), str(value)))
                    ds.append(self.callStore(node, key, value))
        return defer.gatherResults(ds)

    # Fix for None in values for delete
    def rpc_find_value(self, sender, nodeid, key):
        source = Node(nodeid, sender[0], sender[1])
        _log.debug("rpc_find_value sender=%s, source=%s, key=%s" % (sender, source, base64.b64encode(key)))
        self.maybeTransferKeyValues(source)
        self.router.addContact(source)
        exists, value = self.storage.get(key, None)
        if not exists:
            return self.rpc_find_node(sender, nodeid, key)
        return { 'value': value }

    def rpc_append(self, sender, nodeid, key, value):
        source = Node(nodeid, sender[0], sender[1])
        _log.debug("rpc_append sender=%s, source=%s, key=%s, value=%s" % (sender, source, base64.b64encode(key), str(value)))
        self.maybeTransferKeyValues(source)
        self.router.addContact(source)

        try:
            pvalue = json.loads(value)
            self.set_keys.add(key)
            if key not in self.storage:
                _log.debug("%s append key: %s not in storage set value: %s" % (base64.b64encode(nodeid), base64.b64encode(key), pvalue))
                self.storage[key] = value
            else:
                old_value_ = self.storage[key]
                try:
                    old_value = json.loads(old_value_)
                    new_value = list(set(old_value + pvalue))
                except:
                    # When the key have been used for single values it does not contain a list
                    # When have been deleted contains None
                    # Just replace old value
                    old_value = old_value_
                    new_value = pvalue
                _log.debug("%s append key: %s old: %s add: %s new: %s" % (base64.b64encode(nodeid), base64.b64encode(key), old_value, pvalue, new_value))
                self.storage[key] = json.dumps(new_value)
            return True

        except:
            _log.debug("Trying to append something not a JSON coded list %s" % value, exc_info=True)
            return False

    def callAppend(self, nodeToAsk, key, value):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.append(address, self.sourceNode.id, key, value)
        return d.addCallback(self.handleCallResponse, nodeToAsk)

    def rpc_remove(self, sender, nodeid, key, value):
        source = Node(nodeid, sender[0], sender[1])
        _log.debug("rpc_remove sender=%s, source=%s, key=%s, value=%s" % (sender, source, base64.b64encode(key), str(value)))
        self.maybeTransferKeyValues(source)
        self.router.addContact(source)

        try:
            pvalue = json.loads(value)
            self.set_keys.add(key)
            if key in self.storage:
                try:
                    old_value = json.loads(self.storage[key])
                    new_value = list(set(old_value) - set(pvalue))
                except:
                    # When the key have been used for single values or deleted it does not contain a list
                    # Just empty it
                    old_value = self.storage[key]
                    new_value = []
                self.storage[key] = json.dumps(new_value)
                _log.debug("%s remove key: %s old: %s remove: %s new: %s" % (base64.b64encode(nodeid), base64.b64encode(key), old_value, pvalue, new_value))

            return True

        except:
            _log.debug("Trying to remove somthing not a JSON coded list %s" % value, exc_info=True)
            return False

    def callRemove(self, nodeToAsk, key, value):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.remove(address, self.sourceNode.id, key, value)
        return d.addCallback(self.handleCallResponse, nodeToAsk)


class AppendServer(Server):

    def __init__(self, ksize=20, alpha=3, id=None, storage=None):
        storage = storage or ForgetfulStorageFix()
        Server.__init__(self, ksize, alpha, id, storage=storage)
        self.set_keys=set([])
        self.protocol = KademliaProtocolAppend(self.node, self.storage, ksize, set_keys=self.set_keys)
        if kademlia_version != '0.5':
            _log.error("#################################################")
            _log.error("### EXPECTING VERSION 0.5 of kademlia package ###")
            _log.error("#################################################")

    def bootstrap(self, addrs):
        """
        Bootstrap the server by connecting to other known nodes in the network.

        Args:
            addrs: A `list` of (ip, port) `tuple` pairs.  Note that only IP addresses
                   are acceptable - hostnames will cause an error.
        """
        # if the transport hasn't been initialized yet, wait a second
        if self.protocol.transport is None:
            return task.deferLater(reactor, .2, self.bootstrap, addrs)
        else:
            _log.debug("AppendServer.bootstrap(%s)" % addrs)
            return Server.bootstrap(self, addrs)

    def append(self, key, value):
        """
        For the given key append the given list values to the set in the network.
        """
        dkey = digest(key)
        node = Node(dkey)

        def append_(nodes):
            # if this node is close too, then store here as well
            if not nodes or self.node.distanceTo(node) < max([n.distanceTo(node) for n in nodes]):
                try:
                    pvalue = json.loads(value)
                    self.set_keys.add(dkey)
                    if dkey not in self.storage:
                        _log.debug("%s local append key: %s not in storage set value: %s" % (base64.b64encode(node.id), base64.b64encode(dkey), pvalue))
                        self.storage[dkey] = value
                    else:
                        old_value_ = self.storage[dkey]
                        try:
                            old_value = json.loads(old_value_)
                            new_value = list(set(old_value + pvalue))
                        except:
                            # When the key have been used for single values it does not contain a list
                            # When have been deleted contains None
                            # Just replace old value
                            new_value = pvalue
                            old_value = old_value_
                        _log.debug("%s local append key: %s old: %s add: %s new: %s" % (base64.b64encode(node.id), base64.b64encode(dkey), old_value, pvalue, new_value))
                        self.storage[dkey] = json.dumps(new_value)
                except:
                    _log.debug("Trying to append something not a JSON coded list %s" % value, exc_info=True)
            ds = [self.protocol.callAppend(n, dkey, value) for n in nodes]
            return defer.DeferredList(ds).addCallback(self._anyRespondSuccess)

        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            self.log.warning("There are no known neighbors to set key %s" % key)
            _log.debug("There are no known neighbors to set key %s" % key)
            return defer.succeed(False)

        spider = NodeSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return spider.find().addCallback(append_)

    def set(self, key, value):
        """
        Set the given key to the given value in the network.
        """
        _log.debug("setting '%s' = '%s' on network" % (key, value))
        dkey = digest(key)
        node = Node(dkey)

        def store(nodes):
            _log.debug("setting '%s' to %s on %s" % (key, value, map(str, nodes)))
            # if this node is close too, then store here as well
            if (not nodes or self.node.distanceTo(node) < max([n.distanceTo(node) for n in nodes]) or
                dkey in self.storage):
                _log.debug("setting '%s' to %s locally" % (key, value))
                self.storage[dkey] = value
            ds = [self.protocol.callStore(n, dkey, value) for n in nodes]
            return defer.DeferredList(ds).addCallback(self._anyRespondSuccess)

        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            _log.warning("There are no known neighbors to set key %s" % key)
            return defer.succeed(False)
        spider = NodeSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return spider.find().addCallback(store)

    def get(self, key):
        """
        Get a key if the network has it.

        Returns:
            :class:`None` if not found, the value otherwise.
        """
        dkey = digest(key)
        _log.debug("Server:get %s" % base64.b64encode(dkey))
        # if this node has it, return it
        exists, value = self.storage.get(dkey)
        if exists:
            return defer.succeed(value)
        node = Node(dkey)
        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            self.log.warning("There are no known neighbors to get key %s" % key)
            return defer.succeed(None)
        spider = ValueSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return spider.find()

    def remove(self, key, value):
        """
        For the given key remove the given list values from the set in the network.
        """
        dkey = digest(key)
        node = Node(dkey)
        _log.debug("Server:remove %s" % base64.b64encode(dkey))

        def remove_(nodes):
            # if this node is close too, then store here as well
            if not nodes or self.node.distanceTo(node) < max([n.distanceTo(node) for n in nodes]):
                try:
                    pvalue = json.loads(value)
                    self.set_keys.add(dkey)
                    if dkey in self.storage:
                        try:
                            old_value = json.loads(self.storage[dkey])
                            new_value = list(set(old_value) - set(pvalue))
                        except:
                            # When the key have been used for single values or deleted it does not contain a list
                            # Just empty it
                            old_value = self.storage[dkey]
                            new_value = []
                        self.storage[dkey] = json.dumps(new_value)
                        _log.debug("%s local remove key: %s old: %s remove: %s new: %s" % (base64.b64encode(node.id), base64.b64encode(dkey), old_value, pvalue, new_value))
                except:
                    _log.debug("Trying to remove somthing not a JSON coded list %s" % value, exc_info=True)
            ds = [self.protocol.callRemove(n, dkey, value) for n in nodes]
            return defer.DeferredList(ds).addCallback(self._anyRespondSuccess)

        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            self.log.warning("There are no known neighbors to set key %s" % key)
            return defer.succeed(False)

        spider = NodeSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return spider.find().addCallback(remove_)

    def get_concat(self, key):
        """
        Get a key if the network has it. Assuming it is a list that should be combined.

        @return: C{None} if not found, the value otherwise.
        """
        dkey = digest(key)
        # Always try to do a find even if we have it, due to the concatenation of all results
        exists, value = self.storage.get(dkey)
        node = Node(dkey)
        nearest = self.protocol.router.findNeighbors(node)
        _log.debug("Server:get_concat key=%s, value=%s, exists=%s, nbr nearest=%d" % (base64.b64encode(dkey), value, 
                                                                                      exists, len(nearest)))
        if len(nearest) == 0:
            # No neighbors but we had it, return that value
            if exists:
                return defer.succeed(value)
            self.log.warning("There are no known neighbors to get key %s" % key)
            return defer.succeed(None)
        spider = ValueListSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha,
                                      local_value=value if exists else None)
        return spider.find()

class ValueListSpiderCrawl(ValueSpiderCrawl):

    def __init__(self, *args, **kwargs):
        self.local_value = kwargs.pop('local_value', None)
        super(ValueListSpiderCrawl, self).__init__(*args, **kwargs)

    def _nodesFound(self, responses):
        """
        Handle the result of an iteration in C{_find}.
        """
        toremove = []
        foundValues = []
        for peerid, response in responses.items():
            response = RPCFindResponse(response)
            if not response.happened():
                toremove.append(peerid)
            elif response.hasValue():
                foundValues.append((peerid, response.getValue()))
            else:
                peer = self.nearest.getNodeById(peerid)
                self.nearestWithoutValue.push(peer)
                self.nearest.push(response.getNodeList())
        _log.debug("_nodesFound nearestWithoutValue: %s, nearest: %s, toremove: %s" %
                    (self.nearestWithoutValue.getIDs(), self.nearest.getIDs(), toremove))
        self.nearest.remove(toremove)

        if len(foundValues) > 0:
            return self._handleFoundValues(foundValues)
        if self.nearest.allBeenContacted():
            # not found at neighbours!
            if self.local_value:
                # but we had it
                return self.local_value
            else:
                return None
        return self.find()

    def _handleFoundValues(self, jvalues):
        """
        We got some values!  Exciting.  But lets combine them all.  Also,
        make sure we tell the nearest node that *didn't* have
        the value to store it.
        """
        # TODO figure out if we could be more cleaver in what values are combined
        value = None
        _set_op = True
        if self.local_value:
            jvalues.append((None, self.local_value))
        _log.debug("_handleFoundValues %s" % str(jvalues))
        # Filter out deleted values
        jvalues = [v for v in jvalues if v[1] is not None]
        if len(jvalues) > 1:
            args = (self.node.long_id, str(jvalues))
            _log.debug("Got multiple values for key %i: %s" % args)
            try:
                values = [(v[0], json.loads(v[1])) for v in jvalues]
                value_all = []
                for v in values:
                    value_all = value_all + v[1]
                value = json.dumps(list(set(value_all)))
            except:
                # Not JSON coded or list, probably trying to do a get_concat on none set-op data
                # Do the normal thing
                _log.debug("_handleFoundValues ********", exc_info=True)
                valueCounts = Counter([v[1] for v in jvalues])
                value = valueCounts.most_common(1)[0][0]
                _set_op = False
        else:
            try:
                key, value = jvalues[0]
            except:
                value = "[]"  # JSON empty list

        peerToSaveTo = self.nearestWithoutValue.popleft()
        if peerToSaveTo is not None:
            _log.debug("nearestWithoutValue %d" % (len(self.nearestWithoutValue)+1))
            if _set_op:
                d = self.protocol.callAppend(peerToSaveTo, self.node.id, value)
            else:
                d = self.protocol.callStore(peerToSaveTo, self.node.id, value)
            return d.addCallback(lambda _: value)
        # TODO if nearest does not contain the proper set push to it
        return value
