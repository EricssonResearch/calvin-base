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
import os
import hashlib
import base64
from collections import Counter

from twisted.internet import defer, task, reactor
from kademlia.network import Server
from kademlia.protocol import KademliaProtocol
from kademlia import crawling
from kademlia.utils import deferredDict, digest
from kademlia.storage import ForgetfulStorage
from kademlia.node import Node, NodeHeap
from kademlia import version as kademlia_version
from calvin.utilities import certificate

from twisted.python import log
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
from calvin.utilities import runtime_credentials

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)

# Make twisted (rpcudp) logs go to null
log.startLogging(log.NullFile(), setStdout=0)


def logger(node, message, level=None):
    _log.debug("{}:{}:{} - {}".format(node.id.encode("hex"),
                                     node.ip,
                                     node.port,
                                     message))
    #print("{}:{}:{} - {}".format(node.id.encode("hex"),
    #                                 node.ip,
    #                                 node.port,
    #                                 message))

def generate_challenge():
    """ Generate a random challenge of 8 bytes, hex string formated"""
    return os.urandom(8).encode("hex")

def dhtidhex_from_certstring(cert_str):
    nodeid = certificate.cert_DN_Qualifier(certstring=cert_str)
    dhtid = dhtid_from_nodeid(nodeid) 
    dhtidhex=dhtid.encode("hex")
#    _log.debug("dhtidhex_from_certstring returns:\n\tnodeid={}\n\tdhtid={}".format(nodeid, dhtidhex))
    return dhtidhex

def nodeid_from_dhtid(dhtid):
    import uuid as sys_uuid
    nodeid = str(sys_uuid.UUID(dhtid))
#    _log.debug("nodeid_from_dhtid returns:\n\tnodeid={}\n\tdhtid={}".format(nodeid, dhtid))
    return nodeid

def dhtid_from_nodeid(nodeid):
    import uuid as sys_uuid
    dhtid = sys_uuid.UUID(nodeid).bytes
#    _log.debug("dhtid_from_nodeid returns:\n\tnodeid={}\n\tdhtid={}".format(nodeid, dhtid.encode('hex')))
    return dhtid

# Fix for None types in storage
class ForgetfulStorageFix(ForgetfulStorage):
    def get(self, key, default=None):
        self.cull()
        if key in self.data:
            return (True, self[key])
        return (False, default)

def hexify_list(list):
    hex_list=[]
    for value in list:
        hex_list.append(value.encode('hex'))
    return hex_list

def hexify_dict(dict):
    hex_dict=[]
    for key,value in dict.iteritems():
        hex_list.append(value.encode('hex'))
    return hex_list

def hexify_list_of_tuples(list):
    hex_list=[]
    for value1, value2  in list:
        hex_list.append( (value1.encode('hex'), value2) )
    return hex_list

def hexify_list_of_nodes(list):
    hex_list=[]
    for value in list:
        hex_list.append(value[0].encode('hex'))
#                hex_list.append([value[0].encode('hex'), value[1], value[2]])
    return hex_list

class KademliaProtocolAppend(KademliaProtocol):

    def __init__(self, *args, **kwargs):
        _log.debug("KademliaProtocolAppend::__init__:\n\targs={}\n\tkwargs={}".format(args,kwargs))
        self.set_keys = kwargs.pop('set_keys', set([]))

        self.priv_key = None
        self.node_name = kwargs.pop('node_name',None)
        self.runtime_credentials = kwargs.pop('runtime_credentials', None)
        KademliaProtocol.__init__(self, *args, **kwargs)

    #####################
    # Call Functions    #
    #####################

    def callCertFindValue(self, node):
        """
        Asks 'nodeToAsk' for its certificate.
        """
        address = (node.ip, node.port)
        challenge = generate_challenge()
        key = digest("{}cert".format(node))
        _log.debug("KademliaProtocolAppend::callCertFindValue:"
                   "\n\tchallenge generated={}"
                   "\n\tnodeToAsk={}"
                   "\n\tkey={}".format(challenge,
                                              node.id.encode('hex'),
                                              key.encode('hex')))
        try:
            signature = self.runtime_credentials.sign_data(
                                            node.id.encode("hex") + challenge)
        except:
            _log.error("RETNONE: Signing of certFindValue failed")
            return None
        d = self.find_value(address,
                           self.sourceNode.id,
                           key,
                           challenge,
                           signature,
                           self.getOwnCert())
        return d.addCallback(self.handleCertCallResponse,
                            node,
                            challenge)


    def callFindNode(self, nodeToAsk, nodeToFind):
        """
        Asks 'nodeToAsk' for the value 'nodeToFind.id'
        """
#        _log.debug("KademliaProtocolAppend::callFindNode"
#                   "\n\tnodeToAsk={}"
#                   "\n\tnodeToFind={}".format(nodeToAsk.id.encode('hex'),
#                                              nodeToFind.id.encode('hex')))
        address = (nodeToAsk.ip, nodeToAsk.port)
        challenge = generate_challenge()
        try:
            signature = self.runtime_credentials.sign_data(
                                            nodeToAsk.id.encode("hex") + challenge)
            _log.debug("KademliaProtocolAppend::callFindNode We have generated a challenge and signed it"
                       "\n\tnodeToAsk={}"
                       "\n\tnodeToFind={}"
                       "\n\tchallenge={}"
                       "\n\tsignature={}".format(nodeToAsk.id.encode('hex'),
                                                nodeToFind.id.encode('hex'),
                                                challenge,
                                                signature.encode('hex')))
        except:
            _log.error("RETNONE: Signing of findNode failed")
            return None
        d = self.find_node(address,
                          self.sourceNode.id,
                          nodeToFind.id,
                          challenge,
                          signature)
        return d.addCallback(self.handleSignedBucketResponse,
                            nodeToAsk,
                            challenge)

    def callFindValue(self, nodeToAsk, nodeToFind):
        """
        Asks 'nodeToAsk' for the information regarding the node 'nodeToFind'
        """
        address = (nodeToAsk.ip, nodeToAsk.port)
        challenge = generate_challenge()
        _log.debug("KademliaProtocolAppend::callFindValue: Challenge generated:"
               "\n\tchallenge={}"
               "\n\tnodeToAsk={}"
               "\n\tnodeToAsk_long={}"
               "\n\tnodeToFind={}".format(challenge,
                                          nodeToAsk.id.encode('hex'),
                                          nodeToAsk.long_id,
                                          nodeToFind.id.encode('hex')))
        try:
            signature = self.runtime_credentials.sign_data(
                                            nodeToAsk.id.encode("hex") + challenge)
        except:
            _log.error("RETNONE: Signing of findValue failed")
            return None
        d = self.find_value(address,
                           self.sourceNode.id,
                           nodeToFind.id,
                           challenge,
                           signature)
        return d.addCallback(self.handleSignedValueResponse,
                            nodeToAsk,
                            challenge)

    def callPing(self, nodeToAsk, cert=None):
        """
        Sends a ping message to 'nodeToAsk'
        """ 
        address = (nodeToAsk.ip, nodeToAsk.port)
        challenge = generate_challenge()
        _log.debug("KademliaProtocolAppend::callPing Challenge generated:"
                                "\n\tchallenge={}"
                                "\n\tnodeToAsk={}".format(challenge, nodeToAsk.id.encode('hex')))
        try:
            signature = self.runtime_credentials.sign_data(
                                            nodeToAsk.id.encode("hex") + challenge)
        except:
            _log.error("RETNONE: Signing of ping failed")
            return None
        d = self.ping(address,
                     self.sourceNode.id,
                     challenge,
                     signature,
                     cert)
        return d.addCallback(self.handleSignedPingResponse,
                            nodeToAsk,
                            challenge)

    def callStore(self, nodeToAsk, key, value):
        """
        Sends a request for 'nodeToAsk' to store value 'value' with key 'key'
        """   
        address = (nodeToAsk.ip, nodeToAsk.port)
        challenge = generate_challenge()
        try:
            signature = self.runtime_credentials.sign_data(
                                            nodeToAsk.id.encode("hex") + challenge)
        except:
            _log.error("RETNONE: Signing of store failed")
            return None
        _log.debug("KademliaProtocolAppend::callStore: Challenge generated, send store request"
               "\n\tchallenge={}"
               "\n\tsignature={}"
               "\n\tnodeAsking.id={}"
               "\n\tnodeToAsk.id={}"
               "\n\tkey={}"
               "\n\tvalue={}".format(challenge,
                                     signature.encode('hex'),
                                     self.sourceNode.id.encode('hex'),
                                     nodeToAsk.id.encode('hex'),
                                     key.encode("hex"),
                                     value))
        d = self.store(address,
                      self.sourceNode.id,
                      key,
                      value,
                      challenge,
                      signature)
        return d.addCallback(self.handleSignedStoreResponse,
                            nodeToAsk,
                            challenge)

    def callAppend(self, nodeToAsk, key, value):
        """
        Sends a request for 'nodeToAsk' to add value 'value' to key 'key' set
        """   
        address = (nodeToAsk.ip, nodeToAsk.port)
        challenge = generate_challenge()
        _log.debug("KademliaProtocolAppend::callAppend: Challenge generated:"
               "\n\tchallenge={}"
               "\n\tnodeToAsk={}"
               "\n\tnodeAsking.id={}"
               "\n\tkey={}"
               "\n\tvalue={}".format(challenge,
                                     nodeToAsk.id.encode('hex'),
                                     self.sourceNode.id.encode('hex'),
                                     key.encode("hex"),
                                     value))
        try:
            signature = self.runtime_credentials.sign_data(
                                            nodeToAsk.id.encode("hex") + challenge)
        except:
            _log.error("RETNONE: Signing of append failed")
            return None
        d = self.append(address,
                        self.sourceNode.id,
                        key,
                        value,
                        challenge,
                        signature)
        return d.addCallback(self.handleSignedStoreResponse, nodeToAsk, challenge)

    def callRemove(self, nodeToAsk, key, value):
        """
        Sends a request for 'nodeToAsk' to remove value 'value' from key 'key' set
        """   
        address = (nodeToAsk.ip, nodeToAsk.port)
        challenge = generate_challenge()
        _log.debug("KademliaProtocolAppend::callRemove: Challenge generated:"
               "\n\tchallenge={}"
               "\n\tnodeToAsk={}"
               "\n\tkey={}"
               "\n\tvalue={}".format(
                   challenge,
                   nodeToAsk.id.encode('hex'),
                   key.encode("hex"),
                   value))
        try:
            signature = self.runtime_credentials.sign_data(
                                            nodeToAsk.id.encode("hex") + challenge)
        except:
            _log.error("RETNONE: Signing of append failed")
            return None
        d = self.remove(address,
                        self.sourceNode.id,
                        key,
                        value,
                        challenge,
                        signature)
        return d.addCallback(self.handleSignedStoreResponse, nodeToAsk, challenge)

    #####################
    # Response handlers #
    #####################

    def handleCertCallResponse(self, result, node, challenge):
        """
        Handle Certificate responses. `result` is a response value array
        Element 0 contains ??, Element 1 is a dictionary that contains a
        certificate.

        `node` is responding node and `challenge` is the returned
        challenge value.
        Raise ?? exceptions at ?? occation.
        Return results if signatures are valid?
        """
        _log.debug("KademliaProtocolAppend::handleCertCallResponse, result={}, node={}, challenge={}".format(result, node.id.encode('hex'), challenge))
        cert_str = result[1]['value']
        signature = result[1]['signature'].decode('hex')
        if 'value' in result[1]:
            try:
                id = dhtidhex_from_certstring(cert_str)
            except:
                _log.error("RETFALSENONE: Invalid certificate "
                                        "response from {}".format(node.id.encode('hex')))
                return (False, None)
            if node.id.encode('hex') == id:
                try:
                    self.runtime_credentials.verify_signed_data_from_certstring(
                                                                        cert_str,
                                                                        signature,
                                                                        challenge,
                                                                        certificate.TRUSTSTORE_TRANSPORT)
                except:
                    _log.error(
                          "Invalid signature on certificate "
                          "response from {}".format(node.id.encode('hex')))
                self.router.addContact(node)
                self.storeCert(cert_str, id)
                if self.router.isNewNode(node):
                    self.transferKeyValues(node)
            else:
                _log.error("RETFALSENONE: Certificate from {} does not match claimed node id".format(node.id.encode('hex')))
                return (False, None)
        else:
            self.router.removeContact(node)
        return result

    def handleSignedBucketResponse(self, result, node, challenge):
        """
        ???
        `result` is an array and element 1 contains a dict.
        Return None if any error occur and dont tell anyone.
        """
        try:
            hex_result = (result[0], {'bucket': hexify_list_of_nodes(result[1]['bucket']), 'signature':result[1]['signature']})
            _log.debug("KademliaProtocolAppend::handleSignedBucketResponse:"
                                    "\n\tresult={}"
                                    "\n\tnode={}"
                                    "\n\tchallenge={}".format(hex_result,
                                                              node.id.encode('hex'),
                                                              challenge))
        except Exception as err:
            _log.debug("handleSignedBucketResponse: Failed to hexify result, err={}, result={}".format(err, result))
        nodeIdHex = node.id.encode('hex')
        if result[0]:
            if "NACK" in result[1]:
                return (False, self.handleSignedNACKResponse(result, node, challenge))
            elif 'bucket' in result[1] and 'signature' in result[1]:
                cert_stored = self.searchForCertificate(nodeIdHex)
                if cert_stored == None:
                    _log.debug(
                           "RETFALSENONE: Certificate for sender of bucket:"
                           " {} not present in store".format(node.id.encode('hex')))
                    return (False, None)
                try:
                    self.runtime_credentials.verify_signed_data_from_certstring(
                                                                        cert_stored,
                                                                        result[1]['signature'].decode('hex'),
                                                                        challenge,
                                                                        certificate.TRUSTSTORE_TRANSPORT)
                    self.router.addContact(node)
                    newbucket = list()
                    for bucketnode in result[1]['bucket']:
                        buId = bucketnode[0]
                        buIdHex = buId.encode('hex')
                        buIp = bucketnode[1]
                        buPort = bucketnode[2]
                        if not self.certificateExists(buIdHex):
                            nonCertifiedNode = Node(buId,
                                                    buIp,
                                                    buPort)
                            buIdDigest = digest(str(buIdHex))
                            buIdReq = Node(buIdDigest)
                            self.callCertFindValue(nonCertifiedNode)
                        else:
                            newbucket.append(bucketnode)
                    _log.debug("KademliaProtocolAppend::handleSignedBucketResponse:  The signed response was ok"
                                            "\n\tchallenge={}"
                                            "\n\tresult[0]={}"
                                            "\n\tnewbucket={}".format(challenge,
                                                              result[0],
                                                              hexify_list_of_nodes(newbucket)))
                    return (result[0], newbucket)
                except Exception as err:
                    _log.error(
                          "RETFALSENONE: Bad signature for sender of bucket:"
                           "\n\terr={}"
                           "\n\tnode={}".format(err, node))
                    return (False, None)
            else:
                if not result[1]['signature']:
                    _log.debug(
                          "RETFALSENONE: Signature not present"
                          " for sender of bucket: {}".format(node.id.encode('hex')))
                return (False, None)
        else:
            _log.debug(
                  "RETFALSENONE: No response from {}, removing from bucket"
                   "\n\tchallenge={}".format(node.id.encode('hex'), challenge))
            self.router.removeContact(node)
        return (False, None)

    def handleSignedPingResponse(self, result, node, challenge):
        """
        Handler for signed ping responses.
        `result` contains an array
            Element 0 contains ??
            Element 1 contains a dict with message fields.
        Return None on error.
        Return identity of ping response if signature is valid.
        """
        _log.debug("KademliaProtocolAppend::handleSignedPingResponse "
               "\n\tresult={}"
               "\n\tnode={}"
               "\n\tchallenge={}".format(result, node.id.encode('hex'), challenge))
        address = (nodeToAsk.ip, nodeToAsk.port)
        if result[0]:
            if "NACK" in result[1]:
                return self.handleSignedNACKResponse(result,
                                                    node,
                                                    challenge)
            elif 'id' in result[1] and 'signature' in result[1]:
                if result[1]['id'] != node.id:
                    _log.debug(
                          "RETNONE: Pong ID return "
                          "mismatch for {}".format(node.id.encode('hex')))
                    return None
                nodeIdHex = node.id.encode('hex')
                cert_stored = self.searchForCertificate(nodeIdHex)
                if cert_stored == None:
                    _log.debug(
                          "RETNONE: Certificate for sender of pong: {} "
                          "not present in store".format(node.id.encode('hex')))
                    return None
                try: 
                    self.runtime_credentials.verify_signed_data_from_certstring(
                                                                        cert_stored,
                                                                        result[1]['signature'].decode('hex'),
                                                                        payload,
                                                                        certificate.TRUSTSTORE_TRANSPORT)
                    self.router.addContact(node)
                    return result[1]['id']
                except:
                    _log.error(
                          "RETNONE: Bad signature for sender"
                          " of pong: {}".format(node.id.encode('hex')))
                    return None
            else:
                _log.debug(
                      "RETNONE: Signature not present for sender"
                      " of pong: {}".format(node.id.encode('hex')))
                return None
        else:
            _log.debug(
                  "RETNONE: No pong from {}, removing"
                  " from bucket".format(node.id.encode('hex')))
            self.router.removeContact(node)
        return None

    def handleSignedStoreResponse(self, result, node, challenge):
        """
        If we get a response and correctly signed challenge, add
        the node to the routing table.  If we get no response,
        make sure it's removed from the routing table.
        """
        _log.debug("KademliaProtocolAppend::handleSignedStoreResponse:"
               "\n\tresult={}"
               "\n\tnode={}"
               "\n\tchallenge={}".format(result,
                                         node.id.encode('hex'),
                                         challenge))
        if result[0]:
            if "NACK" in result[1]:
                return (False, self.handleSignedNACKResponse(hexify_list_of_tuples(result),
                                                            node,
                                                            challenge))
            nodeIdHex = node.id.encode('hex')
            cert_stored = self.searchForCertificate(nodeIdHex)
            if cert_stored == None:
                _log.debug(
                "RETFALSENONE: Certificate for sender of store confirmation: {}"
                " not present in store".format(node.id.encode('hex')))
                return (False, None)
            try: 
                self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    result[1],
                                                                    challenge,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
                self.router.addContact(node)
                _log.debug("handleSignedStoreResponse - finished OK")
                return (True, True)
            except:
                _log.error(
                      "RETFALSENONE: Bad signature for sender of store"
                      " confirmation: {}".format(node.id.encode('hex')))
                return (False, None)
        else:
            _log.debug(
                  "RETFALSENONE: No store confirmation from {},"
                  " removing from bucket".format(node.id.encode('hex')))
            self.router.removeContact(node)
        return (False, None)

    def handleSignedValueResponse(self, result, node, challenge):
        _log.debug("KademliaProtocolAppend::handleSignedValueResponse"
                                "\n\tresult={}"
                                "\n\tnode={}"
                                "\n\tchallenge={}".format(result,
                                                      node.id.encode('hex'),
                                                      challenge))
        if result[0]:
            if "NACK" in result[1]:
                return (False, self.handleSignedNACKResponse(result,
                                                            node,
                                                            challenge))
            elif 'bucket' in result[1]:
                return self.handleSignedBucketResponse(result,
                                                      node,
                                                      challenge)
            elif 'value' in result[1] and 'signature' in result[1]:
                nodeIdHex = node.id.encode('hex')
                cert_stored = self.searchForCertificate(nodeIdHex)
                if cert_stored == None:
                    _log.debug(
                          "RETFALSENONE: Certificate for sender of value response: {}"
                          " not present in store".format(node.id.encode('hex')))
                    return (False, None)
                try: 
                    self.runtime_credentials.verify_signed_data_from_certstring(
                                                                        cert_stored,
                                                                        result[1]['signature'].decode('hex'),
                                                                        challenge,
                                                                        certificate.TRUSTSTORE_TRANSPORT)
                    self.router.addContact(node)
                    _log.debug("KademliaProtocolAppend::handleSignedValueResponse:  Signed value is ok"
                                            "\n\tresult={}"
                                            "\n\tnode={}"
                                            "\n\tchallenge={}".format(result,
                                                                  node.id.encode('hex'),
                                                                  challenge))
                    return result
                except:
                    _log.error(
                          "RETFALSENONE: Bad signature for sender of "
                          "value response: {}".format(node.id.encode('hex')))
                    return (False, None)
            else:
                _log.debug(
                      "RETFALSENONE: Signature not present for sender "
                      "of value response: {}".format(node.id.encode('hex')))
                return (False, None)
        else:
            _log.debug(
                  "No value response from {}, "
                  "removing from bucket".format(node.id.encode('hex')))
            self.router.removeContact(node)
        return (False, None)

    def handleSignedNACKResponse(self, result, node, challenge):
        _log.debug("KademliaProtocolAppend::handleSignedNACKResponse, result={}, node={}, challenge={}".format(result, node.id.encode('hex'), challenge))
        address = (nodeToAsk.ip, nodeToAsk.port)
        nodeIdHex = node.id.encode('hex')
        cert_stored = self.searchForCertificate(nodeIdHex)
        if cert_stored == None:
            _log.debug(
                  "Certificate for sender of NACK: {} "
                  "not present in store".format(node.id.encode('hex')))
        if "NACK" in result[1]:
            _log.debug(
                  "NACK in Value response")
            try:
                self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    result[1]['signature'].decode('hex'),
                                                                    challenge,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
                self.callPing(node, self.getOwnCert())
                _log.debug("Certificate sent!")
            except:
                _log.error(
                      "Bad signature for sender "
                      "of NACK: {}".format(node.id.encode('hex')))
        _log.debug("RETNONE: handleSignedNACKResponse")
        return None


    #####################
    # RPC Functions     #
    #####################

    def rpc_store(self, sender, nodeid, key, value, challenge, signature):
        _log.debug("KademliaProtocolAppend::rpc_store:"
               "\n\tsender={}"
               "\n\tsource={}"
               "\n\tkey={}"
               "\n\tvalue={}"
               "\n\tchallenge={}"
               "\n\tsignature={}".format(sender,
                                         nodeid.encode('hex'),
                                         key.encode('hex'),
                                         str(value),
                                         challenge,
                                         signature.encode('hex')))
        _log.debug("rpc_store sender=%s, source=%s, key=%s, value=%s" % (sender, nodeid.encode('hex'), key.encode('hex'), str(value)))
        source = Node(nodeid, sender[0], sender[1])
        nodeIdHex = nodeid.encode('hex')
        cert_stored = self.searchForCertificate(nodeIdHex)
        if cert_stored == None:
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error("RETNONE: Failed make signature for store")
                return None
            _log.debug(
                  "Certificate for {} not "
                  "found in store".format(source))
            return {'NACK' : None, "signature" : signature}
        else:
            try:
                sourceNodeIdHex = self.sourceNode.id.encode('hex')
                payload = "{}{}".format(sourceNodeIdHex, challenge)
                self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    signature,
                                                                    payload,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
            except:
                _log.error(
                      "RETNONE: Bad signature for sender of "
                      "store request: {}".format(source))
                return None
            try:
                self.router.addContact(source)
            except Exception as err:
                _log.error("Failed to add contact to router, err={}".format(err))
            self.storage[key] = value
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error(
                      "RETNONE: Signing of rpc_store failed")
                return None
            _log.debug("Signing of rpc_store success")
            return signature

    def rpc_append(self, sender, nodeid, key, value, challenge, signature):
        _log.debug("KademliaProtocolAppend::rpc_append:"
               "\n\tsender={}"
               "\n\tnodeid={}"
               "\n\tkey={}"
               "\n\tvalue={}"
               "\n\tchallenge={}"
               "\n\tsignature={}".format(sender,
                                         nodeid.encode('hex'),
                                         key.encode('hex'),
                                         value,
                                         challenge,
                                         signature.encode('hex')))
        source = Node(nodeid, sender[0], sender[1])
        nodeIdHex = nodeid.encode('hex')
        cert_stored = self.searchForCertificate(nodeIdHex)
        if cert_stored == None:
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error("RETNONE: Failed make signature for append")
                return None
            _log.debug(
                  "Certificate for {} not "
                  "found in store".format(source))
            return {'NACK' : None, "signature" : signature}
        else:
            try:
                sourceNodeIdHex = self.sourceNode.id.encode('hex')
                payload = "{}{}".format(sourceNodeIdHex, challenge)
                self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    signature,
                                                                    payload,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
            except:
                _log.error(
                      "RETNONE: Bad signature for sender of "
                      "append request: {}".format(source))
                return None
            self.router.addContact(source)
            try:
                pvalue = json.loads(value)
                self.set_keys.add(key)
                if key not in self.storage:
                    _log.debug("append key: %s not in storage set value: %s" %
                                            (base64.b64encode(key), pvalue))
                    self.storage[key] = value
                else:
                    old_value_ = self.storage[key]
                    old_value = json.loads(old_value_)
                    new_value = list(set(old_value + pvalue))
                    _log.debug("append key: %s old: %s add: %s new: %s" %
                                            (base64.b64encode(key), old_value, pvalue, new_value))
                    self.storage[key] = json.dumps(new_value)
            except:
                _log.error("RETNONE: Trying to append something not a JSON coded list %s" % value, exc_info=True)
                return None
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error(
                      "RETNONE: Signing of rpc_append failed")
                return None
            return signature



    def rpc_remove(self, sender, nodeid, key, value, challenge, signature):
        _log.debug("KademliaProtocolAppend::rpc_remove"
               "\n\tsender={}"
               "\n\tnodeid={}"
               "\n\tkey={}"
               "\n\tvalue={}"
               "\n\tchallenge={}"
               "\n\tsignature={}".format(sender,
                                         nodeid,
                                         key,
                                         value,
                                         challenge,
                                         signature.encode('hex')))
        source = Node(nodeid, sender[0], sender[1])
        nodeIdHex = nodeid.encode('hex')
        cert_stored = self.searchForCertificate(nodeIdHex)
        if cert_stored == None:
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error("RETNONE: Failed make signature for remove")
                return None
            _log.debug(
                  "Certificate for {} not "
                  "found in store".format(source))
            return {'NACK' : None, "signature" : signature}
        else:
            try:
                sourceNodeIdHex = self.sourceNode.id.encode('hex')
                payload = "{}{}".format(sourceNodeIdHex, challenge)
                self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    signature,
                                                                    payload,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
            except:
                _log.error(
                      "RETNONE: Bad signature for sender of "
                      "remove request: {}".format(source))
                return None
            self.router.addContact(source)
            try:
                pvalue = json.loads(value)
                self.set_keys.add(key)
                if key in self.storage:
                    old_value = json.loads(self.storage[key])
                    new_value = list(set(old_value) - set(pvalue))
                    self.storage[key] = json.dumps(new_value)
                    _log.debug("remove key: %s old: %s add: %s new: %s" %
                                            (base64.b64encode(key), old_value, pvalue, new_value))
            except:
                _log.error("RETNONE: Trying to remove somthing not a JSON coded list %s" % value, exc_info=True)
                return None
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error(
                      "RETNONE: Signing of rpc_remove failed")
                return None
            return signature

    def rpc_find_node(self, sender, nodeid, key, challenge, signature):
        _log.debug("KademliaProtocolAppend::rpc_find_node:"
                               "\n\tsender={}"
                               "\n\tdhtid={}"
                               "\n\tkey={}"
                               "\n\tchallenge={}"
                               "\n\tsignature={}".format(sender,
                                                         nodeid.encode('hex'),
                                                         key.encode('hex'),
                                                         challenge,
                                                         signature.encode('hex')))
        nodeIdHex = nodeid.encode('hex')
        source = Node(nodeid, sender[0], sender[1])
        cert_stored = self.searchForCertificate(nodeIdHex)
        if cert_stored == None:
            _log.erro("No certificate for {} found".format(nodeIdHex))
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error("RETNONE: Failed make signature for find node, challenge={}".format(challenge))
                return None
            _log.debug(
                  "Certificate for {} not found "
                  "in store, challenge={}".format(source, challenge))
            return {'NACK' : None, "signature" : signature}
        else:
            try:
                sourceNodeIdHex = self.sourceNode.id.encode('hex')
                payload = "{}{}".format(sourceNodeIdHex, challenge)
                self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    signature,
                                                                    payload,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
            except:
                _log.error(
                      "RETNONE: Bad signature for sender of "
                      "find_node: {}, challenge={}".format(source, challenge))
                return None
            _log.debug("KademliaProtocolAppend::rpc_find_node: signature of challenge was ok, addContact, challenge={}".format(challenge))
            self.router.addContact(source)
            node = Node(key)
            bucket = map(list, self.router.findNeighbors(node, exclude=source))
            _log.debug("KademliaProtocolAppend::rpc_find_node: bucket={}. Let us now sign challenge={}".format(hexify_list_of_nodes(bucket), challenge))
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except Exception as err:
                _log.error(
                      "RETNONE: Signing of rpc_find_node failed, err={}, challenge={}".format(err, challenge))
                return None
            value = {'bucket': bucket, 'signature': signature.encode('hex')}
            try:
                hex_buckets=[]
                for b in bucket:
                    hex_buckets.append(b[0].encode('hex'))
            except Exception as err:
                _log.error("Failed to hexify buckets, err={}, challenge={}".format(err, challenge))
                hex_buckets=None
            _log.debug("KademliaProtocolAppend::rpc_find_node: we have found the bucket, signed the challenge and will now return it"
                               "\n\tdhtid={}"
                               "\n\tkey={}"
                               "\n\thex_buckets={}"
                               "\n\treturned value={}"
                               "\n\tchallenge={}"
                               "\n\tsignature={}".format(nodeid.encode('hex'),
                                                         key.encode('hex'),
                                                         hex_buckets,
                                                         value,
                                                         challenge,
                                                         signature.encode('hex')))
            return value

    def rpc_find_value(self, sender, nodeid, key, challenge, signature, cert_str=None):
        """
        ???
        Verifying received `challenge` and `signature` using
        supplied signature or stored signature derived from `nodeid`.
        """
        _log.debug("KademliaProtocolAppend::rpc_find_value:"
               "\n\tsender={}"
               "\n\tdhtid={}"
               "\n\tkey={}"
               "\n\tchallenge={}"
               "\n\tsignature={}"
               "\n\tcert_str included={}".format(sender,
                                         nodeid.encode('hex'),
                                         key.encode('hex'),
                                         challenge,
                                         signature.encode('hex'),
                                         cert_str != None))
        source = Node(nodeid, sender[0], sender[1])
        nodeIdHex = nodeid.encode('hex')
        cert_stored = self.searchForCertificate(nodeIdHex)
        if cert_stored == None:
            sourceNodeIdHex = self.sourceNode.id.encode("hex")

            if key == digest("{}cert".format(self.sourceNode.id)) and \
                                                        cert_str != None:
            # If the senders certificate is not in store,
            # the only allowed action is to ask it for its certificate
                try:
                    #verify certificate chain
                    self.runtime_credentials.verify_certificate(cert_str, certificate.TRUSTSTORE_TRANSPORT)
                    id = dhtidhex_from_certstring(cert_str)
                    if id != nodeIdHex:
                        _log.debug(
                              "RETNONE: Explicit certificate in find_value "
                              "from {} does not match nodeid, challenge={}".format(source, challenge))
                        return None
                    sourceNodeIdHex = self.sourceNode.id.encode('hex')
                    payload = "{}{}".format(sourceNodeIdHex, challenge)
                    self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_str,
                                                                    signature,
                                                                    payload,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
                    self.storeCert(cert_str, nodeIdHex)
                except:
                    _log.error(
                          "RETNONE: Invalid certificate "
                          "request: {}, challenge={}".format(source, challenge))
                    return None
            else:
                try:
                    signature = self.runtime_credentials.sign_data(challenge)
                except:
                    _log.error("RETNONE: Failed make signature for find value, challenge={}".format(challenge))
                    return None
                _log.debug(
                      "Certificate for {} not "
                      "found in store, challenge={}".format(source, challenge))
                return { 'NACK' : None, 'signature': signature.encode('hex')}
        else:
            try:
                sourceNodeIdHex = self.sourceNode.id.encode('hex')
                payload = "{}{}".format(sourceNodeIdHex, challenge)
                # Verifying stored certificate with signature.
                self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    signature,
                                                                    payload,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
            except:
                _log.error(
                      "RETNONE: Bad signature for sender of "
                      "find_value: {}, challenge={}".format(source, challenge))
                return None
        _log.debug("KademliaProtocolAppend::rpc_find_value: signed challenge ok, addContact, challenge={}".format(challenge))
        self.router.addContact(source)
        exists, value = self.storage.get(key, None)
        _log.debug("KademliaProtocolAppend::rpc_find_value: we tried to get values locally"
                   "\n\texist={}"
                   "\n\tvalue={}"
                   "\n\tchallenge={}".format(exists, value, challenge))
        if not exists:
            _log.debug(
                  "Key {} not in store, forwarding, challenge={}".format(key.encode('hex'), challenge))
            return self.rpc_find_node(sender,
                                     nodeid,
                                     key,
                                     challenge,
                                     signature)
        else:
            try:
                signature = self.runtime_credentials.sign_data(challenge)
            except:
                _log.error(
                      "RETNONE: Signing of rpc_find_value failed, challenge={}".format(challenge))
                return None
            _log.debug("KademliaProtocolAppend::rpc_find_value: we will now return signed value"
                       "\n\tchallenge={}"
                       "\n\tvalue={}"
                       "\n\tsignature={}".format(challenge, value, signature.encode('hex')))
            return { 'value': value, 'signature': signature.encode('hex') }

    def rpc_ping(self, sender, nodeid, challenge, signature, cert_str=None):
        """
        This function is ???
        Verify `cert_str` certificate with CA from trust store.
        Verify `signature` of `challenge`.
        Store certificate if `cert_str` is verified.

        """
        _log.debug("KademliaProtocolAppend::rpc_ping:"
               "\n\tself.sourceNode.id={}"
               "\n\tsender={}"
               "\n\tnodeid={}"
               "\n\tchallenge={}"
               "\n\tsignature={}"
               "\n\tcert_str included={}".format(self.sourceNode.id.encode('hex'),
                                                 sender,
                                                 nodeid.encode('hex'),
                                                 challenge,
                                                 signature.encode("hex"),
                                                 cert_str != None))
        source = Node(nodeid, sender[0], sender[1])
        nodeIdHex = nodeid.encode("hex")
        if cert_str != None:
            try:
                self.runtime_credentials.verify_certificate(cert_str, certificate.TRUSTSTORE_TRANSPORT)
                # Ensure that the CA of the received certificate is trusted
                id = dhtidhex_from_certstring(cert_str)
                if id != nodeIdHex:
                    _log.debug(
                          "RETNONE: Explicit certificate in ping from {} "
                          "does not match nodeid\n\tid from cert={}\n\tid in ping={}, challenge={}".format(source, id, nodeIdHex, challenge))
                    return None
                sourceNodeIdHex = self.sourceNode.id.encode('hex')
                payload = "{}{}".format(sourceNodeIdHex, challenge)
                try:
                    self.runtime_credentials.verify_signed_data_from_certstring(
                                                                        cert_str,
                                                                        signature,
                                                                        payload,
                                                                        certificate.TRUSTSTORE_TRANSPORT)
                except Exception as err:
                    _log.error("Failed to verify signed ping, err={}"
                               "\n\tcert={}"
                               "\n\tsignature={}"
                               "\n\tpayload={}"
                               "\n\tchallenge={}".format(err,cert_str, signature.encode("hex"), payload, challenge))
                    raise
                if not self.certificateExists(nodeid):
                    self.storeCert(cert_str, nodeid)
                    self.transferKeyValues(source)
            except Exception as e:
                _log.error(
                      "RETNONE: Bad signature for sender of ping with "
                      "explicit certificate: {}, err={}, challenge={}".format(source, e, challenge))
                return None
        else:
            cert_stored = self.searchForCertificate(nodeIdHex)
            if cert_stored == None:
                try:
                    signature = self.runtime_credentials.sign_data(challenge)
                except:
                    _log.error(
                          "RETNONE: Failed make signature for ping, challenge={}".format(challenge))
                    return None
                _log.debug(
                      "Certificate for {} not found "
                      "in store, challenge={}".format(source, challenge))
                return {'NACK' : None, "signature" : signature}
            else:
                try:
                    sourceNodeIdHex = self.sourceNode.id.encode('hex')
                    payload = "{}{}".format(sourceNodeIdHex, challenge)
                    self.runtime_credentials.verify_signed_data_from_certstring(
                                                                        cert_stored,
                                                                        signature,
                                                                        payload,
                                                                        certificate.TRUSTSTORE_TRANSPORT)
                except:
                    _log.error(
                          "RETNONE: Bad signature for sender of "
                          "ping: {}, challenge={}".format(source, challenge))
                    return None
        try:
            signature = self.runtime_credentials.sign_data(challenge)
        except:
            _log.error("RETNONE: Signing of rpc_ping failed, challenge={}".format(challenge))
            return None
        return { 'id': self.sourceNode.id.encode('hex'), 'signature': signature.encode('hex') }


    #####################
    # MISC              #
    #####################

    def certificateExists(self, id):
        """
        Returns however the certificate for a
        given id exists in the own DHT storage.
        """
#        _log.debug("certificateExist")
        return digest("{}cert".format(id)) in self.storage

    def searchForCertificate(self, id):
        """
        Seaches the internal storage for the certificate
        for a node with a given ID. If only one certificate
        is found to match the ID, this is returned.
        If none or several is found, None is returned.
        """
#        _log.debug("searchForCertificate, id={}".format(id))
        try:
            key = digest("{}cert".format(id))
            if key in self.storage:
#                _log.debug("Certificate found in local storage {}".format(self.storage.get(digest("{}cert".format(id)))))
                result = self.storage.get(key)
                cert_list = list(result)[1]
                cert_str = cert_list[0]
                return cert_str 
            else:
 #               _log.debug("Certificate not in local storage, search for it in persistant storage")
                nodeid = nodeid_from_dhtid(id)
                return self.runtime_credentials.get_certificate_locally(cert_name=nodeid)

        except Exception as err:
            _log.error("searchForCertificate: Failed search, err={}, id={}".format(err, id))
            return None

    def _timeout(self, msgID):
        self._outstanding[msgID][0].callback((False, None))
        del self._outstanding[msgID]

    def transferKeyValues(self, node):
        """
        Given a new node, send it all the keys/values it
        should be storing. @param node: A new node that
        just joined (or that we just found out about).
        Process:
        For each key in storage, get k closest nodes.
        If newnode is closer than the furtherst in that
        list, and the node for this server is closer than
        the closest in that list, then store the key/value
        on the new node (per section 2.5 of the paper)
        """
        _log.debug("**** transfer key values to node {}****".format(node.id.encode('hex')))
        for key, value in self.storage.iteritems():
            keynode = Node(digest(key))
            neighbors = self.router.findNeighbors(keynode)
            _log.debug("transfer? target=%s nbr neighbors=%d, key=%s, value=%s" % (node.id.encode('hex'), len(neighbors), key.encode('hex'), str(value)))
            if len(neighbors) > 0:
                newNodeClose = node.distanceTo(keynode) < neighbors[-1].distanceTo(keynode)
                thisNodeClosest = self.sourceNode.distanceTo(keynode) < neighbors[0].distanceTo(keynode)
            if len(neighbors) == 0 or (newNodeClose and thisNodeClosest):
                if key in self.set_keys:
                    _log.debug("transfer append key value key={}, value={}".format(key.encode('hex'), value))
                    self.callAppend(node, key, value)
                    return None
                else:
                    _log.debug("transfer store key value key={}, value={}".format(key.encode('hex'), value))
                    self.callStore(node, key, value)
                    return None

    def storeOwnCert(self, cert_str):
        """
        Stores the string representation of the nodes own
        certificate in the DHT.
        """
#        _log.debug("storeOwnCert")
        sourceNodeIdHex = self.sourceNode.id.encode("hex")
        self.storage[digest("{}cert".format(self.sourceNode.id))] = [cert_str]

    def storeCert(self, cert_str, id):
        """
        Takes a string representation of a PEM-encoded certificate and
        a nodeid as input. If the string is a valid PEM-encoded certificate
        and the CA of the the certificate is present in the trustedStore of
        this node, the certificate is stored in the DHT and written to disk
        for later use.
        """
#        _log.debug("storeCert"
#                "\n\tid={}".format(id.encode('hex')))
        try:
            self.runtime_credentials.verify_certificate(cert_str, certificate.TRUSTSTORE_TRANSPORT)
        except:
            _log.error("The certificate for {} is not signed by a trusted CA!".format(id.encode('hex')))
            return
        exists = self.storage.get(digest("{}cert".format(id)))
        if not exists[0]:
            dkey = digest("{}cert".format(id))
            _log.debug("storeCert  Cert not stored, let's store it at dkey={}".format(dkey.encode('hex')))
            self.storage[dkey] = [cert_str]
            store_path = self.runtime_credentials.store_others_cert(certstring=cert_str)
            _log.debug("storeCert: Also stored certificate persistently at: {}".format(store_path))
#        else:
#            _log.debug("storeCert: certificate for {} is already in local store".format(id.encode('hex')))

    def getOwnCert(self):
        """
        Retrieves the nodes own certificate from the nodes DHT-storage and
        returns it.
        """
#        _log.debug("getOwnCert")
        sourceNodeIdHex = self.sourceNode.id.encode("hex")
        return self.storage[digest("{}cert".format(self.sourceNode.id))][0]

class AppendServer(Server):

    def __init__(self, ksize=20, alpha=3, id=None, storage=None, node_name=None, runtime_credentials=None):
        _log.debug("AppendServer::__init__:\n\tid={}\n\tnode_name={}\n\truntime_credentials={}".format(id.encode('hex'), node_name, runtime_credentials))
        storage = storage or ForgetfulStorageFix()
        Server.__init__(self, ksize, alpha, id, storage=storage)
        self.set_keys=set([])
        self.node_name=node_name
        self.runtime_credentials=runtime_credentials
        self.protocol = KademliaProtocolAppend(self.node, self.storage, ksize, node_name=self.node_name, set_keys=self.set_keys, runtime_credentials=self.runtime_credentials)
        if kademlia_version != '0.5':
            _log.error("#################################################")
            _log.error("### EXPECTING VERSION 0.5 of kademlia package ###")
            _log.error("#################################################")

    def bootstrap(self, addrs):
        """
        Bootstrap the server by connecting to other known nodes in the network.

        Args:
            addrs: A `list` of (ip, port, cert) tuples.  Note that only IP addresses
                   are acceptable - hostnames will cause an error.
        """
        _log.debug("AppendServer::bootstrap, addrs={}".format(addrs))
        # if the transport hasn't been initialized yet, wait a second
        if self.protocol.transport is None:
            return task.deferLater(reactor,
                                    1,
                                    self.bootstrap,
                                    addrs)

        #id is in dhtid in hex
        def initTable(results, challenge, id):
            _log.debug("AppendServer::bootstrap::initTable:"
                       "\n\tresults={}"
                       "\n\tchallenge={}"
                       "\n\tself.node.id={}"
                       "\n\tid={}".format(results, challenge, self.node.id.encode('hex'), id))
            nodes = []
            for addr, result in results.items():
                ip = addr[0]
                port = addr[1]
                if result[0]:
                    resultSign = result[1]['signature'].decode('hex')
                    resultId = result[1]['id'].decode('hex')
                    resultIdHex = resultId.encode('hex')
#                    data = self.protocol.certificateExists(resultId)
#                    if not data:
#                        identifier = digest("{}cert".format(resultId))
#                        self.protocol.callCertFindValue(Node(resultId,
#                                                            ip,
#                                                            port),
#                                                       Node(identifier))
#                    else:
                    cert_stored = self.protocol.searchForCertificate(resultIdHex)
                    try:
                        self.runtime_credentials.verify_signed_data_from_certstring(
                                                                    cert_stored,
                                                                    resultSign,
                                                                    challenge,
                                                                    certificate.TRUSTSTORE_TRANSPORT)
                    except:
                        logger(self.protocol.sourceNode, "Failed verification of challenge during bootstrap\n\toriginal challenge={}\n\treturned from ={}\n\treturned signature={}\n\terr={}".format(challenge, resultId.encode('id'), resultSign.encode('hex'), err))
                    _log.debug("AppendServer::bootstrap::initTable: the challenge was correctly signed, let's append to nodes")
                    nodes.append(Node(resultId,
                                     ip,
                                     port))
            _log.debug("AppendServer::bootstrap::initTable: let's now call NodeSpiderCrawl with nodes={}".format(nodes))
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
            cert_str = data[2]
            logger(self.protocol.sourceNode, "\n########### DOING BOOTSTRAP ###########")
            try:
                id = dhtidhex_from_certstring(cert_str)
                signature = self.runtime_credentials.sign_data("{}{}".format(id, challenge))
                _log.debug("AppendServer::bootstrap: We have generated a challenge and signed it, let's now ping target\n\tself.node.id={}\n\ttarget id={}\n\tchallenge={}\n\tsignature={}".format(self.node.id.encode('hex'), id, challenge, signature.encode('hex')))
                ds[addr] = self.protocol.ping(addr,
                                             self.node.id,
                                             challenge,
                                             signature,
                                             self.protocol.getOwnCert())
                self.protocol.storeCert(cert_str, id)
            except Exception as err:
                logger(self.protocol.sourceNode, "Bootstrap failed, err={}".format(err))
            if not id:
                return deferredDict(ds)
            node = Node(id.decode("hex"), data[0], data[1])
            if self.protocol.router.isNewNode(node):
                return deferredDict(ds).addCallback(initTable,
                                                   challenge,
                                                   id)
        _log.debug("AppendServer::bootstrap  No addrs supplied")
        return deferredDict(ds)

    def append(self, key, value):
        """
        For the given key append the given list values to the set in the network.
        """
        try:
            dkey = digest(key)
        except Exception as err:
            _log.error("Failed to calculate digest of key={}, err={}".format(key, err))
            raise
        _log.debug("AppendServer::append"
                   "\n\tkey={}"
                   "\n\tdkey={}"
                   "\n\tvalue={}".format(key, dkey.encode('hex'), value))
        node = Node(dkey)

        def append_(nodes):
            nodes_hex=[n.id.encode('hex') for n in nodes]
            _log.debug("AppendServer::append::append_"
                       "\n\tkey={}"
                       "\n\tdkey={}"
                       "\n\tvalue={}"
                       "\n\tnodes={}".format(key, dkey.encode('hex'), value, nodes_hex))
            # if this node is close too, then store here as well
            if not nodes or self.node.distanceTo(node) < max([n.distanceTo(node) for n in nodes]):
                _log.debug("AppendServer::append::append_: this node is close, store")
                try:
                    pvalue = json.loads(value)
                    self.set_keys.add(dkey)
                    if dkey not in self.storage:
                        _log.debug("%s local append key: %s not in storage set value: %s" % (base64.b64encode(node.id), base64.b64encode(dkey), pvalue))
                        self.storage[dkey] = value
                    else:
                        old_value_ = self.storage[dkey]
                        old_value = json.loads(old_value_)
                        new_value = list(set(old_value + pvalue))
                        _log.debug("{} local append "
                                   "\n\tkey={}"
                                   "\n\told={}"
                                   "\n\tadd={}"
                                   "\n\tnew={}".format(base64.b64encode(node.id), base64.b64encode(dkey), old_value, pvalue, new_value))
                        self.storage[dkey] = json.dumps(new_value)
                except:
                    _log.debug("Trying to append something not a JSON coded list %s" % value, exc_info=True)
            else:
                _log.debug("AppendServer::append::append_: this node is not close, don't store")
            ds = [self.protocol.callAppend(n, dkey, value) for n in nodes]
            return defer.DeferredList(ds).addCallback(self._anyRespondSuccess)

        nearest = self.protocol.router.findNeighbors(node)
        if len(nearest) == 0:
            self.log.warning("There are no known neighbors to set key %s" % key)
            _log.debug("There are no known neighbors to set key %s" % key)
            return defer.succeed(False)
        _log.debug("AppendServer::append: Let us find Neighbors by doing a NodeSpiderCrawl, then call append_")
        spider = NodeSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha)
        return spider.find().addCallback(append_)

    def set(self, key, value):
        """
        Set the given key to the given value in the network.
        """
        try:
            dkey = digest(key)
        except Exception as err:
            _log.error("Failed to calculate digest of key={}, err={}".format(key, err))
            raise
#        _log.debug("AppendServer::set:"
#                   "\n\tkey={}"
#                   "\n\tdkey={}"
#                   "\n\tvalue={}".format(key, dkey.encode('hex'), value))
        node = Node(dkey)

        def store(nodes):
            _log.debug("AppendServer::set Setting '%s' on %s" % (key, [x.id.encode('hex') for x in nodes]))
#            _log.debug("AppendServer::set Setting '%s' on %s" % (key, map(str, nodes)))
            # if this node is close too, then store here as well
            if not nodes or self.node.distanceTo(node) < max([n.distanceTo(node) for n in nodes]):
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
        try:
            dkey = digest(key)
        except Exception as err:
            _log.error("Failed to calculate digest of key={}, err={}".format(key, err))
            raise
        _log.debug("AppendServer::get"
                   "\n\tkey={}"
                   "\n\tdkey={}".format(key, dkey.encode('hex')))
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
        try:
            dkey = digest(key)
        except Exception as err:
            _log.error("Failed to calculate digest of key={}, err={}".format(key, err))
            raise
        node = Node(dkey)
        _log.debug("Server:remove %s" % base64.b64encode(dkey))
        _log.debug("AppendServer::remove"
                   "\n\tkey={}"
                   "\n\tdkey={}"
                   "\n\tvalue={}".format(key, dkey.encode('hex'), value))

        def remove_(nodes):
            # if this node is close too, then store here as well
            if not nodes or self.node.distanceTo(node) < max([n.distanceTo(node) for n in nodes]):
                try:
                    pvalue = json.loads(value)
                    self.set_keys.add(dkey)
                    if dkey in self.storage:
                        old_value = json.loads(self.storage[dkey])
                        new_value = list(set(old_value) - set(pvalue))
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
        try:
            dkey = digest(key)
        except Exception as err:
            _log.error("Failed to calculate digest of key={}, err={}".format(key, err))
            raise
        # Always try to do a find even if we have it, due to the concatenation of all results
        exists, value = self.storage.get(dkey)
        node = Node(dkey)
        nearest = self.protocol.router.findNeighbors(node)
        _log.debug("Server:get_concat "
                   "\n\tkey={}"
                   "\n\tdkey={}"
                   "\n\tlocal value={}"
                   "\n\texists={}"
                   "\n\tnbr nearest={}".format(key,
                                               dkey.encode('hex'),
                                               value,
                                               exists,
                                               len(nearest)))
        if len(nearest) == 0:
            # No neighbors but we had it, return that value
            if exists:
                return defer.succeed(value)
            self.log.warning("There are no known neighbors to get key %s" % key)
            return defer.succeed(None)
        _log.debug("Let's now invoke ValueListSpiderCrawl to search for key")
        spider = ValueListSpiderCrawl(self.protocol, node, nearest, self.ksize, self.alpha,
                                      local_value=value if exists else None)
        return spider.find()


class SpiderCrawl(crawling.SpiderCrawl):
    def __init__(self, protocol, node, peers, ksize, alpha):
        """
        Create a new C{SpiderCrawl}er.

        Args:
            protocol: A :class:`~kademlia.protocol.KademliaProtocol` instance.
            node: A :class:`~kademlia.node.Node` representing the key we're looking for
            peers: A list of :class:`~kademlia.node.Node` instances that provide the entry point for the network
            ksize: The value for k based on the paper
            alpha: The value for alpha based on the paper
        """
        from kademlia.log import Logger
        self.protocol = protocol
        self.ksize = ksize
        self.alpha = alpha
        self.node = node
        # Changed from ksize to (ksize + 1) * ksize
        self.nearest = NodeHeap(self.node, (self.ksize+1) * self.ksize)
        self.lastIDsCrawled = []
        self.log = Logger(system=self)
        self.log.debug("creating spider with peers: %s" % peers)
        self.nearest.push(peers)


class NodeSpiderCrawl(SpiderCrawl, crawling.NodeSpiderCrawl):
    # Make sure that our SpiderCrawl __init__ gets called (crawling.NodeSpiderCrawl don't have __init__)
    pass


class ValueSpiderCrawl(SpiderCrawl, crawling.ValueSpiderCrawl):
    def __init__(self, protocol, node, peers, ksize, alpha):
        # Make sure that our SpiderCrawl __init__ gets called
        SpiderCrawl.__init__(self, protocol, node, peers, ksize, alpha)
        # copy crawling.ValueSpiderCrawl statement besides calling original SpiderCrawl.__init__
        self.nearestWithoutValue = NodeHeap(self.node, 1)


    def _nodesFound(self, responses):
        """
        Handle the result of an iteration in _find.
        """
        _log.debug("ValueSpiderCrawl::_nodesFound")
        toremove = []
        foundValues = []
        for peerid, response in responses.items():
            response = crawling.RPCFindResponse(response)
            if not response.happened():
                toremove.append(peerid)
            elif response.hasValue():
                foundValues.append(response.getValue())
            else:
                peer = self.nearest.getNodeById(peerid)
                self.nearestWithoutValue.push(peer)
                self.nearest.push(response.getNodeList())
        self.nearest.remove(toremove)
        # Changed that first try to wait for alpha responses
        if len(foundValues) >= self.alpha:
            return self._handleFoundValues(foundValues) 
        if self.nearest.allBeenContacted():
            if len(foundValues) > 0: 
                return self._handleFoundValues(foundValues) 
            else:
                return None

        return self.find()


class ValueListSpiderCrawl(ValueSpiderCrawl):

    def __init__(self, *args, **kwargs):
        _log.debug("ValueListwSpiderCrawl::__init__"
                   "\n\targs={}"
                   "\n\tkwargs={}".format(args, kwargs))
        self.local_value = kwargs.pop('local_value', None)
        super(ValueListSpiderCrawl, self).__init__(*args, **kwargs)

    def find(self, previouslyFoundValues=None):
        """
        Find either the closest nodes or the value requested.
        """
        return self._find(self.protocol.callFindValue, previouslyFoundValues=previouslyFoundValues)

    def _find(self, rpcmethod, previouslyFoundValues=None):
        """
         Get either a value or list of nodes.

         Args:
            rpcmethod: The protocol's callfindValue or callFindNode.

         The process:
           1. calls find_* to current ALPHA nearest not already queried nodes,
                adding results to current nearest list of k nodes.
          2. current nearest list needs to keep track of who has been queried already
           sort by nearest, keep KSIZE
         3. if list is same as last time, next call should be to everyone not
          yet queried
        4. repeat, unless nearest list has all been queried, then ur done
        """
        _log.info("crawling with nearest: {}  ".format(str(tuple(self.nearest)), previouslyFoundValues))
        count = self.alpha
        if self.nearest.getIDs() == self.lastIDsCrawled:
            _log.info("last iteration same as current - checking all in list now")
            count = len(self.nearest)
        self.lastIDsCrawled = self.nearest.getIDs()

        ds = {}
        for peer in self.nearest.getUncontacted()[:count]:
            ds[peer.id] = rpcmethod(peer, self.node)
            self.nearest.markContacted(peer)
        return deferredDict(ds).addCallback(self._nodesFound, previouslyFoundValues=previouslyFoundValues)

    def _nodesFound(self, responses, previouslyFoundValues=None):
        """
        Handle the result of an iteration in C{_find}.
        """

        hex_responses={}
        try:
            for key,value in responses.iteritems():
                hex_responses[key.encode('hex')] = []
                if isinstance(value[1], dict):
                    hex_responses[key.encode('hex')].append(value[1])
                elif isinstance(value[1], list):
                    for item in value[1]:
                        hex_responses[key.encode('hex')].append(item[0].encode('hex'))
            _log.debug("ValueListwSpiderCrawl::_nodesFound"
                       "\n\thex_responses={}"
                       "\n\tpreviouslyFoundValues={}".format(hex_responses, hexify_list_of_tuples(previouslyFoundValues)))
        except Exception as err:
            _log.debug("Failed to hexify _nodesFound, err={}"
                       "\n\tresponses={}"
                       "\n\tpreviouslyFoundValues={}".format(err, responses, previouslyFoundValues))
        toremove = []
        foundValues = []
        for peerid, response in responses.items():
            response = crawling.RPCFindResponse(response)
            if not response.happened():
                toremove.append(peerid)
            elif response.hasValue():
                foundValues.append((peerid, response.getValue()))
            else:
                peer = self.nearest.getNodeById(peerid)
                self.nearestWithoutValue.push(peer)
                self.nearest.push(response.getNodeList())
        _log.debug("ValueListwSpiderCrawl::_nodesFound "
                   "\n\tfoundValues={}"
                   "\n\tnearestWithoutValue={}"
                   "\n\tnearest={}"
                   "\n\ttoremove={}".format(hexify_list_of_tuples(foundValues),
                                            hexify_list(self.nearestWithoutValue.getIDs()),
                                            hexify_list(self.nearest.getIDs()),
                                            hexify_list(toremove)))
        #Add found values from previous rounds to recently found values
        try:
            if previouslyFoundValues:
                foundValues.extend(previouslyFoundValues)
        except Exception as err:
            _log.error("Failed to add previously found values, err={}".format(err))
        try:
            _log.debug("ValueListwSpiderCrawl::_nodesFound "
                       "\n\tfoundValues={}"
                       "\n\tnearestWithoutValue={}"
                       "\n\tnearest={}"
                       "\n\ttoremove={}".format(hexify_list_of_tuples(foundValues),
                                                hexify_list(self.nearestWithoutValue.getIDs()),
                                                hexify_list(self.nearest.getIDs()),
                                                hexify_list(toremove)))
        except Exception as err:
            _log.debug("ValueListwSpiderCrawl::_nodesFound Failed to hexify"
                       "\n\tfoundValues={}"
                       "\n\tnearestWithoutValue={}"
                       "\n\tnearest={}"
                       "\n\ttoremove={}".format(foundValues,
                                                self.nearestWithoutValue.getIDs(),
                                                self.nearest.getIDs(),
                                                toremove))
        self.nearest.remove(toremove)

        # Changed that first try to wait for alpha responses
        if len(foundValues) >= self.alpha: 
            _log.debug("ValueListwSpiderCrawl::_nodesFound foundValues>=alpha, so return foundValues={}".format(foundValues))

            return self._handleFoundValues(foundValues) 
        if self.nearest.allBeenContacted():
            if len(foundValues) > 0: 
                result = self._handleFoundValues(foundValues) 
                _log.debug("ValueListwSpiderCrawl::_nodesFound allBeenContacted and foundValues>0, result={}".format(result))
                return result
#                return self._handleFoundValues(foundValues) 
            else:
                # not found at neighbours!
                if self.local_value:
                    _log.debug("ValueListwSpiderCrawl::_nodesFound allBeenContacted, not found at neighbours, but we have it, result={}".format(self.local_value))
                    # but we had it
                    return self.local_value
                else:
                    _log.debug("ValueListwSpiderCrawl::_nodesFound Value NOT found anywhere")
                    return None
        _log.debug("ValueListwSpiderCrawl::_nodesFound we are not satisfied, let's ask more nodes"
                   "\n\tfoundValues={}".format(hexify_list_of_tuples(foundValues)))
        return self.find(previouslyFoundValues = foundValues if len(foundValues)>0 else None)

    def _handleFoundValues(self, jvalues):
        """
        We got some values!  Exciting.  But lets combine them all.  Also,
        make sure we tell the nearest node that *didn't* have
        the value to store it.
        """
        def hexify_and_print_jvalues():
            hex_jvalues=[]
            try:
                for value in jvalues:
                    if not value[0]:
                        hex_jvalues.append( (None, value[1]) )
                    else:
                        hex_jvalues.append( (value[0].encode('hex'), value[1]) )
                _log.debug("ValueListwSpiderCrawl::_handleFoundValues"
                           "\n\thex_jvalues={}".format(hex_jvalues))
            except Exception as err:
                _log.error("ValueListwSpiderCrawl::_handleFoundValues  Failed to hexify, err={}".format(err))
        # TODO figure out if we could be more cleaver in what values are combined
        value = None
        _set_op = True
        if self.local_value:
            jvalues.append((None, self.local_value))
#        _log.debug("ValueListwSpiderCrawl::_handleFoundValues %s" % str(jvalues))
        hexify_and_print_jvalues()

        if len(jvalues) != 1:
            args = (self.node.long_id, str(jvalues))
            _log.debug("Got multiple values for key {}: {}".format(self.node.id.encode('hex'),str(jvalues)))
            try:
                values = [(v[0], json.loads(v[1])) for v in jvalues]
                value_all = []
                for v in values:
                    value_all = value_all + v[1]
                value = json.dumps(list(set(value_all)))
            except:
                # Not JSON coded or list, probably trying to do a get_concat on none set-op data
                # Do the normal thing
                _log.debug("ValueListwSpiderCrawl::_handleFoundValues ********", exc_info=True)
                valueCounts = Counter([v[1] for v in jvalues])
                value = valueCounts.most_common(1)[0][0]
                _set_op = False
        else:
            key, value = jvalues[0]

        peerToSaveTo = self.nearestWithoutValue.popleft()
        if peerToSaveTo is not None:
            _log.debug("ValueListwSpiderCrawl::nearestWithoutValue %d" % (len(self.nearestWithoutValue)+1))
            if _set_op:
                d = self.protocol.callAppend(peerToSaveTo, self.node.id, value)
            else:
                d = self.protocol.callStore(peerToSaveTo, self.node.id, value)
            return d.addCallback(lambda _: value)
        # TODO if nearest does not contain the proper set push to it
        _log.debug("ValueListwSpiderCrawl::_handleFoundValues will now return value\n\tvalue={}".format(value))
        return value
