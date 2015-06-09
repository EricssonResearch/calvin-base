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

import json
import uuid

from twisted.internet import defer
from kademlia.network import Server
from kademlia.protocol import KademliaProtocol
from kademlia.crawling import NodeSpiderCrawl
from kademlia.utils import digest
from kademlia.node import Node


class KademliaProtocolAppend(KademliaProtocol):

    def rpc_append(self, sender, mid, nodeid, key, value):
        source = Node(nodeid, sender[0], sender[1])
        self.router.addContact(source)
        self.log.debug("got a append request from %s, storing value" %
                       str(sender))

        try:
            pvalue = json.loads(value)

            if key not in self.storage:
                self.storage[key] = value
                self.storage[mid] = True
            else:
                if mid in self.storage:
                    return False

                old_value = json.loads(self.storage[key])
                self.storage[key] = json.dumps(list(set(old_value + pvalue)))
                self.storage[mid] = True

            return True

        except:
            import traceback
            traceback.print_exc()
            return False

    def callAppend(self, nodeToAsk, mid, key, value):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.append(address, mid, self.sourceNode.id, key, value)
        return d.addCallback(self.handleCallResponse, nodeToAsk)

    def rpc_remove(self, sender, mid, nodeid, key, value):
        source = Node(nodeid, sender[0], sender[1])
        self.router.addContact(source)
        self.log.debug("got a remove request from %s, storing value" %
                       str(sender))

        try:
            pvalue = json.loads(value)

            if key in self.storage:
                if mid in self.storage:
                    return False

                old_value = json.loads(self.storage[key])
                self.storage[key] = json.dumps(list(set(old_value) - set(pvalue)))
                self.storage[mid] = True

            return True

        except:
            import traceback
            traceback.print_exc()
            return False

    def callRemove(self, nodeToAsk, mid, key, value):
        address = (nodeToAsk.ip, nodeToAsk.port)
        d = self.remove(address, mid, self.sourceNode.id, key, value)
        return d.addCallback(self.handleCallResponse, nodeToAsk)


class AppendServer(Server):

    def __init__(self, ksize=20, alpha=3, id=None, storage=None):
        Server.__init__(self, ksize, alpha, id, storage)
        self.protocol = KademliaProtocolAppend(self.node, self.storage, ksize)

    def append(self, key, value):
        """
        For the given key append the given list values to the set in the network.
        """
        self.log.debug("appending '%s' = '%s' on network" % (key, value))
        dkey = digest(key)

        def append(nodes, mid):
            self.log.info("setting '%s' on %s" % (key, map(str, nodes)))

            mid = uuid.uuid1().hex

            ds = [self.protocol.callAppend(node, mid, dkey, value) for node in nodes]
            return defer.DeferredList(ds).addCallback(self._anyRespondSuccess)

        node = Node(dkey)
        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            self.log.warning("There are no known neighbors to set key %s" % key)
            return defer.succeed(False)

        spider = NodeSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return spider.find().addCallback(append, "hej")

    def remove(self, key, value):
        """
        For the given key remove the given list values from the set in the network.
        """
        self.log.debug("removing '%s' = '%s' on network" % (key, value))
        dkey = digest(key)

        def remove(nodes, mid):
            self.log.info("setting '%s' on %s" % (key, map(str, nodes)))

            mid = uuid.uuid1().hex

            ds = [self.protocol.callRemove(node, mid, dkey, value) for node in nodes]
            return defer.DeferredList(ds).addCallback(self._anyRespondSuccess)

        node = Node(dkey)
        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            self.log.warning("There are no known neighbors to set key %s" % key)
            return defer.succeed(False)

        spider = NodeSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return spider.find().addCallback(remove, "hej")
