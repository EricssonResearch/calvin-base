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

import os
import traceback
import random
try:
    import pydot
except:
    pydot = None
import hashlib
import OpenSSL.crypto

from calvin.utilities import calvinlogger
from calvin.runtime.south.plugins.storage.twistedimpl.securedht import append_server
from calvin.runtime.south.plugins.storage.twistedimpl.securedht import dht_server
from calvin.runtime.south.plugins.storage.twistedimpl.securedht import service_discovery_ssdp
from calvin.utilities import certificate

from kademlia.node import Node
from kademlia.utils import deferredDict, digest
from kademlia.crawling import NodeSpiderCrawl

from calvin.utilities import calvinconfig

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)

def generate_challenge():
    """ Generate a random challenge of 8 bytes, hex string formated"""
    return os.urandom(8).encode("hex")

class evilAutoDHTServer(dht_server.AutoDHTServer):

    def __init__(self, *args, **kwargs):
        super(evilAutoDHTServer, self).__init__(*args, **kwargs)
        self.cert_conf = certificate.Config(_conf.get("security", "certificate_conf"),
                                            _conf.get("security", "certificate_domain")).configuration

    def start(self, iface='', network=None, bootstrap=None, cb=None, type=None, name=None):
        if bootstrap is None:
            bootstrap = []
        name_dir = os.path.join(self.cert_conf["CA_default"]["runtimes_dir"], name)
        filename = os.listdir(os.path.join(name_dir, "mine"))
        st_cert = open(os.path.join(name_dir, "mine", filename[0]), 'rt').read()
        cert_part = st_cert.split(certificate.BEGIN_LINE)
        certstr = "{}{}".format(certificate.BEGIN_LINE, cert_part[1])
        try:
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                  certstr)
        except:
            logger(self.sourceNode,
                  "Certificate creating failed at startup")
        key = cert.digest("sha256")
        newkey = key.replace(":", "")
        bytekey = newkey.decode("hex")

        if network is None:
            network = _conf.get_in_order("dht_network_filter", "ALL")

        if network is None:
            network = _conf.get_in_order("dht_network_filter", "ALL")
        self.dht_server = dht_server.ServerApp(evilAppendServer, bytekey[-20:])
        ip, port = self.dht_server.start(iface=iface)


        dlist = []
        dlist.append(self.dht_server.bootstrap(bootstrap))

        self._ssdps = service_discovery_ssdp.SSDPServiceDiscovery(iface,
                                                                 cert=certstr)
        dlist += self._ssdps.start()

        _log.debug("Register service %s %s:%s" % (network, ip, port))
        self._ssdps.register_service(network, ip, port)

        _log.debug("Set client filter %s" % (network))
        self._ssdps.set_client_filter(network)

        start_cb = service_discovery_ssdp.defer.Deferred()

        def bootstrap_proxy(addrs):
            def started(args):
                _log.debug("DHT Started %s" % (args))
                if not self._started:
                    service_discovery_ssdp.reactor.callLater(.2,
                                                            start_cb.callback,
                                                            True)
                if cb:
                    service_discovery_ssdp.reactor.callLater(.2,
                                                            cb,
                                                            True)
                self._started = True

            def failed(args):
                _log.debug("DHT failed to bootstrap %s" % (args))
                #reactor.callLater(.5, bootstrap_proxy, addrs)

            _log.debug("Trying to bootstrap with %s" % (repr(addrs)))
            d = self.dht_server.bootstrap(addrs)
            d.addCallback(started)
            d.addErrback(failed)

        def start_msearch(args):
            _log.debug("** msearch %s args: %s" % (self, repr(args)))
            service_discovery_ssdp.reactor.callLater(0,
                                                    self._ssdps.start_search,
                                                    bootstrap_proxy,
                                                    stop=False)

        # Wait until servers all listen
        dl = service_discovery_ssdp.defer.DeferredList(dlist)
        dl.addBoth(start_msearch)
        self.dht_server.kserver.protocol.evilType = type
        self.dht_server.kserver.protocol.sourceNode.port = port
        self.dht_server.kserver.protocol.sourceNode.ip = "0.0.0.0"
        self.dht_server.kserver.name = name
        self.dht_server.kserver.protocol.name = name
        self.dht_server.kserver.protocol.storeOwnCert(certstr)
        self.dht_server.kserver.protocol.setPrivateKey()

        return start_cb



class evilKademliaProtocolAppend(append_server.KademliaProtocolAppend):
    def _timeout(self, msgID):
        self._outstanding[msgID][0].callback((False, None))
        del self._outstanding[msgID]

    def callPing(self, nodeToAsk, id=None):
        address = (nodeToAsk.ip, nodeToAsk.port)
        challenge = generate_challenge()
        try:
            private = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                    self.priv_key,
                                                    '')
            signature = OpenSSL.crypto.sign(private,
                                           challenge,
                                           "sha256")
        except:
            "Signing ping failed"
        if id:
            decider = random.random()
            if decider < 0.5:
                self.ping(address, id, challenge, signature, self.getOwnCert())
            else:
                self.ping(address, id, challenge, signature)
        else:
                d = self.ping(address, self.sourceNode.id, challenge, signature, self.getOwnCert())
        return True

    def turn_evil(self, evilPort):
        old_ping = self.rpc_ping
        old_find_node = self.rpc_find_node
        old_find_value = self.rpc_find_value
        self.router.node.port = evilPort;
        if self.evilType == "poison":
            self.rpc_find_node = self.poison_rpc_find_node
            self.rpc_find_value = self.poison_rpc_find_value
            self.false_neighbour_list = []
            for i in range(0, 30):
                fakeid = hashlib.sha1(str(random.getrandbits(255))).digest()
                fake_neighbour = [fakeid,
                                 '10.0.0.9',
                                 self.router.node.port]
                self.false_neighbour_list.append(fake_neighbour)
            _log.debug("Node with port {} prepared to execute "
                       "poisoning attack".format(self.router.node.port))
        elif self.evilType == "insert":
            self.rpc_find_node = self.sybil_rpc_find_node
            self.rpc_find_value = self.poison_rpc_find_value
            ends = bytearray([0x01, 0x02, 0x03])
            self.false_neighbour_list = []
            for i in range(0, 9):
                if i < 3:
                    key = digest("APA")
                elif i > 5:
                    key = digest("KANIN")
                else:
                    key = digest("KOALA")
                key = key[:-1] + bytes(ends[i % 3])
                self.false_neighbour_list.append((key,
                                                 '10.0.0.9',
                                                 self.router.node.port))
            _log.debug("Node with port {} prepared to execute node "
                       "insertion attack".format(self.router.node.port))
        elif self.evilType == "eclipse":
            self.rpc_find_node = self.eclipse_rpc_find_node
            self.rpc_find_value = self.eclipse_rpc_find_value
            self.closest_neighbour = map(list,
                                        self.router.findNeighbors((self.router.node)))
            self.false_neighbour_list = []
            for i in range(0, 10):
                fakeid = hashlib.sha1(str(random.getrandbits(255))).digest()

                self.false_neighbour_list.append((fakeid,
                                                 '10.0.0.9',
                                                 self.router.node.port))
            _log.debug("Node with port {} prepared to execute eclipse "
                       "attack on {}".format(self.router.node.port,
                                            self.closest_neighbour[0][2]))
        elif self.evilType == "sybil":
            self.rpc_find_node = self.sybil_rpc_find_node
            self.rpc_find_value = self.poison_rpc_find_value
            self.false_neighbour_list = []
            for i in range(0, 30):
                fakeid = [hashlib.sha1(str(random.getrandbits(255))).digest()]
                fake_neighbour = [fakeid, '10.0.0.9', self.router.node.port]
                self.false_neighbour_list.append(fake_neighbour)
            _log.debug("Node with port {} prepared to execute "
                       "Sybil attack".format(self.router.node.port))

    def poison_routing_tables(self):
        fakeid = hashlib.sha1(str(random.getrandbits(255))).digest()
        self.neighbours = map(list, self.router.findNeighbors(Node(fakeid),
                                                             k=20))
        my_randoms = random.sample(xrange(len(self.neighbours)), 1)
        for nodeToAttack in my_randoms: 
            for nodeToImpersonate in range(0, len(self.neighbours)):
                if nodeToImpersonate != nodeToAttack:
                    node = Node(self.neighbours[nodeToAttack][0],
                               self.neighbours[nodeToAttack][1],
                               self.neighbours[nodeToAttack][2])
                    self.callPing(node, self.neighbours[nodeToImpersonate][0])


    # def eclipse(self):
    #     self.neighbours = map(list, self.router.findNeighbors(Node(hashlib.sha1(str(random.getrandbits(255))).digest()),k=20))
    #     for nodeToAttack in range(0, len(self.neighbours)):
    #         self.ping((self.neighbours[nodeToAttack][1], self.neighbours[nodeToAttack][2]), self.closest_neighbour[0][0], self.getOwnCert())
    #         self.ping((self.closest_neighbour[0][1], self.closest_neighbour[0][2]), self.neighbours[nodeToAttack][0], self.getOwnCert())

    # def sybil(self, node):
    #     self.ping((node[0], node[1]), hashlib.sha1(str(random.getrandbits(255))).digest(), self.getOwnCert())

    # def sybil_rpc_find_node(self, sender, nodeid, key, challenge, signature):
    #     self.log.info("finding neighbors of %i in local table" % long(nodeid.encode('hex'), 16))
    #     source = Node(nodeid, sender[0], sender[1])
    #     self.maybeTransferKeyValues(source)
    #     self.router.addContact(source)
    #     self.false_neighbour_list = random.sample(self.false_neighbour_list, len(self.false_neighbour_list))
    #     return self.false_neighbour_list

    # def eclipse_rpc_find_node(self, sender, nodeid, key, challenge, signature):
    #     self.log.info("finding neighbors of %i in local table" % long(nodeid.encode('hex'), 16))
    #     source = Node(nodeid, sender[0], sender[1])
    #     _log.debug("eclipse rpc_find_node sender=%s, source=%s, key=%s" % (sender, source, base64.b64encode(key)))
    #     self.maybeTransferKeyValues(source)
    #     self.router.addContact(source)
    #     node = Node(key)
    #     decider = random.random()
    #     if decider < 0.1:
    #         self.eclipse()
    #     self.neighbours = map(list, self.router.findNeighbors(Node(hashlib.sha1(str(random.getrandbits(255))).digest()),k=20))
    #     neighbourList = list(self.neighbours)
    #     if long(nodeid.encode('hex'), 16) != long(self.closest_neighbour[0][0].encode('hex'), 16):
    #         for i in range(0, len(neighbourList)):
    #             if neighbourList[i][0] is self.closest_neighbour[0][0]:
    #                 neighbourList[i] = (neighbourList[i][0], neighbourList[i][1], self.router.node.port)
    #     else:
    #         for i in range(0, len(neighbourList)):
    #             neighbourList[i] = (neighbourList[i][0], neighbourList[i][1], self.router.node.port)
    #     mergedlist = []
    #     mergedlist.extend(neighbourList)
    #     mergedlist.extend(self.false_neighbour_list)
    #     self.neighbours = random.sample(mergedlist, len(mergedlist))
    #     self.neighbours = list(mergedlist)
    #     return self.neighbours

    def poison_rpc_find_node(self, sender, nodeid, key, challenge, signature):
        source = Node(nodeid, sender[0], sender[1])
        # self.maybeTransferKeyValues(source)
        self.router.addContact(source)
        node = Node(key)
        decider = random.random()
        fakeid = hashlib.sha1(str(random.getrandbits(255))).digest()
        self.neighbours = map(list, self.router.findNeighbors(Node(fakeid),k=20))
        if decider < 0.1:
            self.poison_routing_tables()
        elif decider > 0.95:
            fakeid1 = hashlib.sha1(str(random.getrandbits(255))).digest()
            fakeid2 = hashlib.sha1(str(random.getrandbits(255))).digest()
            self.find_value((self.neighbours[0][1], self.neighbours[0][2]),
                           fakeid1,
                           fakeid2,
                           challenge,
                           signature)
        elif decider > 0.9:
            self.find_node((self.neighbours[0][1], self.neighbours[0][2]),
                          nodeid,
                          self.neighbours[0][0],
                          challenge,
                          signature)
        neighbourList = list(self.neighbours)
        for i in range(0, len(neighbourList)):
            neighbourList[i] = [neighbourList[i][0],
                               neighbourList[i][1],
                               self.router.node.port]
        mergedlist = []
        mergedlist.extend(neighbourList)
        mergedlist.extend(self.false_neighbour_list)
        try:
            private = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                  self.priv_key,
                                                  '')
            signature = OpenSSL.crypto.sign(private,
                                           challenge,
                                           "sha256")
        except:
            _log.debug("signing poison find node failed")
        return { 'bucket' : mergedlist , 'signature' : signature }

    def poison_rpc_find_value(self, sender, nodeid, key, challenge, signature):
        value = self.storage[digest(str(self.sourceNode.id.encode("hex").upper()) + "cert")]
        if key == digest("APA") or \
           key == digest("KANIN") or \
           key == digest("KOALA"):
            logger(self.sourceNode,
                   "Attacking node with port {} sent back "
                   "forged value".format(self.router.node.port))
            value = "apelsin"
        try:
            private = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                  self.priv_key,
                                                  '')
            signature = OpenSSL.crypto.sign(private,
                                           challenge,
                                           "sha256")
        except:
            _log.debug("signing poison find value failed")
        return { 'value': value, 'signature': signature }

    # def eclipse_rpc_find_value(self, sender, nodeid, key, challenge, signature):
    #     source = Node(nodeid, sender[0], sender[1])
    #     if long(nodeid.encode('hex'), 16) != long(self.closest_neighbour[0][0].encode('hex'), 16):
    #         _log.debug("Attacking node with port {} received value request from non-eclipsed node".format(self.router.node.port))
    #         self.maybeTransferKeyValues(source)
    #         self.router.addContact(source)
    #         exists, value = self.storage.get(key, None)
    #         if not exists:
    #             return self.rpc_find_node(sender, nodeid, key, challenge, signature)
    #         else:
    #             return { 'value': value }
    #     else:
    #         _log.debug("Attacking node with port {} received value request from eclipsed node".format(self.router.node.port))
    #         return { 'value' : 'apelsin' }


class evilAppendServer(append_server.AppendServer):
    def __init__(self, ksize=20, alpha=3, id=None, storage=None):
        storage = storage or append_server.ForgetfulStorageFix()
        append_server.Server.__init__(self,
                                     ksize,
                                     alpha,
                                     id,
                                     storage=storage)
        self.protocol = evilKademliaProtocolAppend(self.node,
                                                  self.storage,
                                                  ksize)

    def bootstrap(self, addrs):
        """
        Bootstrap the server by connecting to other known nodes in the network.
        Args:
            addrs: A `list` of (ip, port) `tuple` pairs.  Note that only IP addresses
                   are acceptable - hostnames will cause an error.
        """
        # if the transport hasn't been initialized yet, wait a second
        # _log.debug("bootstrap"
        if self.protocol.transport is None:
            return append_server.task.deferLater(service_discovery_ssdp.reactor,
                                                1,
                                                self.bootstrap,
                                                addrs)

        def initTable(results, challenge, id):
            nodes = []
            for addr, result in results.items():
                ip = addr[0]
                port = addr[1]
                if result[0]:
                    resultId = result[1]['id']
                    resultIdHex = resultId.encode('hex').upper()
                    resultSign = result[1]['signature']
                    data = self.protocol.certificateExists(resultIdHex)
                    if not data:
                        identifier = "{}cert".format(resultIdHex)
                        self.protocol.callCertFindValue(Node(resultId,
                                                            ip,
                                                            port),
                                                       Node(identifier))
                    else:
                        cert_stored = self.protocol.searchForCertificate(resultIdHex)
                        try:
                            OpenSSL.crypto.verify(cert_stored,
                                                 resultSign,
                                                 challenge,
                                                 "sha256")
                        except:
                            traceback.print_exc()
                        nodes.append(Node(resultId, ip, port))
            spider = NodeSpiderCrawl(self.protocol,
                                    self.node,
                                    nodes,
                                    self.ksize,
                                    self.alpha)
            return spider.find()

        ds = {}
        challenge = generate_challenge()
        id = None
        if addrs:
            data = addrs[0]
            addr = (data[0], data[1])
            try:
                cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                      data[2])
                fingerprint = cert.digest("sha256")
                id = fingerprint.replace(":", "")[-40:]
                private = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                      self.protocol.priv_key,
                                                      '')
                signature = OpenSSL.crypto.sign(private,
                                                "{}{}".format(id, challenge),
                                                "sha256")
                ds[addr] = self.protocol.ping(addr,
                                             self.node.id,
                                             challenge,
                                             signature,
                                             self.protocol.getOwnCert())
            except:
                logger(self.protocol.sourceNode, "Certificate creation failed")
            self.protocol.storeCert(data[2], id)
            node = Node(id.decode("hex"), data[0], data[1])
            if self.protocol.router.isNewNode(node):
                return deferredDict(ds).addCallback(initTable, challenge, id)
        return deferredDict(ds)

def drawNetworkState(name, servers, amount_of_servers):
    """Save image describinh network of `servers` as `name`."""
    if pydot is None:
        return
    graph = pydot.Dot(graph_type='digraph',
                     nodesep=0,
                     ranksep=0,
                     rankdir="BT")
    for servno in range(0, amount_of_servers):
        rndnode = Node(hashlib.sha1(str(random.getrandbits(255))).digest())
        findNeighbors = servers[servno].dht_server.kserver.protocol.router.findNeighbors
        neighbors = map(tuple, findNeighbors(rndnode, k=50))
        for neighbor in neighbors:
            printPort = servers[servno].dht_server.port.getHost().port
            edge = pydot.Edge(str(printPort),
                             str(neighbor[2]),
                             label=str(neighbor[0].encode('hex')[-4:]))
            graph.add_edge(edge)
    graph.write_png(name)

def logger(node, message, level=None):
    _log.debug("{}:{}:{} - {}".format(node.id.encode("hex").upper(),
                                     node.ip,
                                     node.port,
                                     message))
    # print("{}:{}:{} - {}".format(node.id.encode("hex").upper(), node.ip, node.port, message))
