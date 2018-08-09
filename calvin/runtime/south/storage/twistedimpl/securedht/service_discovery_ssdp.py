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

import time
import traceback
import platform
import random
import socket
import netifaces

from calvin.utilities import calvinlogger

from calvin.runtime.south.storage.twistedimpl.securedht.service_discovery import ServiceDiscoveryBase
#from calvin.runtime.south.storage.twistedimpl.securedht.security_discovery_exchange import Ca

from twisted.internet.protocol import DatagramProtocol
from twisted.web.http import datetimeToString
from twisted.internet import reactor, defer

_log = calvinlogger.get_logger(__name__)

SSDP_ADDR = '239.255.255.250'
SSDP_PORT = 1900

__version_info__ = (0, 6, 7)
__version__ = '.'.join(map(str, __version_info__))

SERVER_ID = ','.join([platform.system(),
                      platform.release(),
                      'UPnP/1.0,Calvin UPnP framework',
                      __version__])
SERVICE_UUID = '1693326a-abb9-11e4-8dfb-9cb654a16426'
CA_SERVICE_UUID = '58532fde-e793-11e5-965d-7cd1c3da1305'

MS_BOOTSTRAP =    ('M-SEARCH * HTTP/1.1\r\nHOST: %s:%d\r\nMAN: "ssdp:discover"\r\n' +
         'MX: 2\r\nST: uuid:%s\r\n\r\n') %\
        (SSDP_ADDR, SSDP_PORT, SERVICE_UUID)

MS_CA = ('M-SEARCH * HTTP/1.1\r\nHOST: %s:%d\r\nMAN: "ssdp:discover"\r\n' +
         'MX: 2\r\nST: uuid:%s\r\n\r\n') %\
        (SSDP_ADDR, SSDP_PORT, CA_SERVICE_UUID)

MS = {SERVICE_UUID: MS_BOOTSTRAP, CA_SERVICE_UUID: MS_CA}

MS_BOOTSTRAP_RESP = 'HTTP/1.1 200 OK\r\n' + \
            'USN: %s::upnp:rootdevice\r\n' % SERVICE_UUID + \
            'SERVER: %s\r\n' + \
            'last-seen: %s\r\n' + \
            'EXT: \r\n' + \
            'SERVICE: %s\r\n' + \
            'LOCATION: %s\r\n' + \
            'CACHE-CONTROL: max-age=1800\r\n' + \
            'ST: uuid:%s\r\n' % SERVICE_UUID + \
            'DATE: %s\r\n'

MS_CA_RESP = 'HTTP/1.1 200 OK\r\n' + \
            'USN: %s::upnp:rootdevice\r\n' % CA_SERVICE_UUID + \
            'SERVER: %s\r\n' + \
            'last-seen: %s\r\n' + \
            'EXT: \r\n' + \
            'LOCATION: %s\r\n' + \
            'CACHE-CONTROL: max-age=1800\r\n' + \
            'ST: uuid:%s\r\n' % CA_SERVICE_UUID + \
            'DATE: %s\r\n'

MS_RESP = {SERVICE_UUID: MS_BOOTSTRAP_RESP, CA_SERVICE_UUID: MS_CA_RESP}

def parse_http_response(data):

    """ don't try to get the body, there are reponses without """
    header = data.split('\r\n\r\n')[0]

    lines = header.split('\r\n')
    cmd = lines[0].split(' ')
    lines = map(lambda x: x.replace(': ', ':', 1), lines[1:])
    lines = filter(lambda x: len(x) > 0, lines)

    headers = [x.split(':', 1) for x in lines]
    headers = dict(map(lambda x: (x[0].lower(), x[1]), headers))

    return cmd, headers


class ServerBase(DatagramProtocol):
    def __init__(self, node_id, control_uri, ips, d=None):
        _log.info("Serverbase::_init_: \n\tnode_id={}\n\tcontrol_uri={}\n\tips={}\n\tdserver={}".format(node_id, control_uri, ips, d))
        self._services = {}
        self._dstarted = d
        self.ignore_list = []
        self.ips = ips
        self._msearches_resp = {sid: {} for sid in MS.keys()}
        self._node_id = node_id
        self._control_uri = control_uri

    def startProtocol(self):
        if self._dstarted:
            reactor.callLater(0, self._dstarted.callback, True)

    def datagramReceived(self, datagram, address):
        # Broadcast
        try:
            cmd, headers = parse_http_response(datagram)
            _log.debug("ServerBase::Received %s, %s from %r" % (cmd, headers, address, ))

            if cmd[0] == 'M-SEARCH' and cmd[1] == '*':

                _log.debug("Ignore list %s ignore %s" % (self.ignore_list, address not in self.ignore_list))
                # Only reply to our requests
                if SERVICE_UUID in headers['st'] and address not in self.ignore_list:

                    for k, addrs in self._services.items():
                        for addr in addrs:
                            # Only tell local about local
                            if addr[0] == "127.0.0.1" and address[0] != "127.0.0.1":
                                continue
                            response = MS_RESP[SERVICE_UUID] % ('%s:%d' % addr, str(time.time()),
                                                                k, self._control_uri + "/node/" + self._node_id, datetimeToString())
                            if "cert" in self._msearches_resp[SERVICE_UUID].keys():
                                response += "CERTIFICATE: {}\r\n\r\n".format(self._msearches_resp[SERVICE_UUID]["cert"])
                            _log.debug("ServerBase::Sending response: %s" % repr(response))
                            delay = random.randint(0, min(5, int(headers['mx'])))
                            reactor.callLater(delay, self.send_it,
                                                  response, address)
                elif CA_SERVICE_UUID in headers['st'] and address not in self.ignore_list\
                    and self._msearches_resp[CA_SERVICE_UUID]["sign"]:
                    for k, addrs in self._services.items():
                        for addr in addrs:
                            # Only tell local about local
                            if addr[0] == "127.0.0.1" and address[0] != "127.0.0.1":
                                continue
                            try:
                                response = MS_RESP[CA_SERVICE_UUID] % (str(addr),
                                                                    str(time.time()),
                                                                    self._control_uri + "/node/" + self._node_id,
                                                                    datetimeToString())
                            except Exception as err:
                                _log.error("Failed to create response, err={}".format(err))
                                raise
                            _log.debug("ServerBase::Sending response: %s" % repr(response))
                            delay = random.randint(0, min(5, int(headers['mx'])))
                            reactor.callLater(delay, self.send_it,
                                                  response, address)
        except Exception as err:
            _log.exception("SSDP search received, but failed handling, err={}".format(err))

    def update_params(self, service_uuid, **kwargs):
        self._msearches_resp[service_uuid].update(kwargs)

    def add_service(self, service, ip, port):
        # Service on all interfaces
        if ip in ["0.0.0.0", ""]:
            self._services[service] = []
            for a in self.ips:
                _log.debug("Add service %s, %s:%s" % (service, a, port))
                self._services[service].append((a, port))
        else:
            _log.debug("Add service %s, %s:%s" % (service, ip, port))
            self._services[service] = [(ip, port)]

    def remove_service(self, service):
        if service in self._services:
            del self._services[service]

    def set_ignore_list(self, list_):
        self.ignore_list = list_

    def send_it(self, response, destination):
        try:
            if self.transport:
                self.transport.write(response, destination)
            else:
                _log.debug("No transport yet!")
        except (AttributeError, socket.error), msg:
            _log.exception("Error in send %s" % repr(msg))

    def stop(self):
        pass


class ClientBase(DatagramProtocol):
    def __init__(self, dclient=None):
        self._dstarted = dclient
        self._service = None
        self._msearches = {sid: {'cb': None, 'stopped': False, 'stop': False} for sid in MS.keys()}

    def startProtocol(self):
        if self._dstarted:
            reactor.callLater(0, self._dstarted.callback, True)

    def datagramReceived(self, datagram, address):
        # Broadcast
        cmd, headers = parse_http_response(datagram)
        _log.debug("ClientBase::Received %s, %s from %r" % (cmd, headers, address, ))
        if cmd[0].startswith('HTTP/1.') and cmd[1] == '200':
            if SERVICE_UUID in headers['st']:
                c_address = headers['server'].split(':')
                c_address[1] = int(c_address[1])
                try:
                    cert = headers['certificate'].split(':')
                    c_address.extend(cert)
                except KeyError:
                    pass
                # Filter on service calvin networks
                if self._service is None or self._service == headers['service']:

                    _log.debug("ClientBase::Received service %s from %s" %
                               (headers['service'], c_address, ))

                    if c_address:
                        if self._msearches[SERVICE_UUID]['cb']:
                            self._msearches[SERVICE_UUID]['cb']([tuple(c_address)])
                        if self._msearches[SERVICE_UUID]['stop']:
                            self.stop(SERVICE_UUID)

            elif CA_SERVICE_UUID in headers['st']:
                _log.error("Deprecated")
#                c_address = headers['server'].split(':')
#                c_address[1] = int(c_address[1])
#                try:
#                    cert = headers['certificate']
#                    c_address.append(cert)
#                except KeyError:
#                    pass
#                # FIXME do we need service filtering for signed certificates
#                if c_address and not self.is_stopped(CA_SERVICE_UUID):
#                    _log.debug("Signed Cert %s" % c_address)
#                    _log.debug("CA search data: %s" % self._msearches[CA_SERVICE_UUID])
#                    if self._msearches[CA_SERVICE_UUID]['cb']:
#                        self._msearches[CA_SERVICE_UUID]['cb'](tuple(c_address))
#                    if self._msearches[CA_SERVICE_UUID]['stop']:
#                        self.stop(CA_SERVICE_UUID)

    def set_callback(self, service_uuid, callback):
        self._msearches[service_uuid]['cb'] = callback

    def set_service(self, service):
        self._service = service

    def is_stopped(self, service_uuid):
        return self._msearches[service_uuid]['stopped']

    def set_autostop(self, service_uuid, stop=True):
        self._msearches[service_uuid]['stop'] = stop

    def stop(self, service_uuid):
        self._msearches[service_uuid]['stopped'] = True


class SSDPServiceDiscovery(ServiceDiscoveryBase):
    def __init__(self, node_id, control_uri, iface='', ignore_self=True):
        super(SSDPServiceDiscovery, self).__init__()

        self.ignore_self = ignore_self
        self.iface = '' #iface
        self.ssdp = None
        self.port = None
        self.searches = {}
        self.iface_send_list = []
        self._node_id = node_id
        self._control_uri = control_uri

        if self.iface in ["0.0.0.0", ""]:
            for a in netifaces.interfaces():
                addrs = netifaces.ifaddresses(a)
                # Ipv4 for now
                if netifaces.AF_INET in addrs:
                    for a in addrs[netifaces.AF_INET]:
                        self.iface_send_list.append(a['addr'])
        else:
            self.iface_send_list.append(iface)

    def start(self):
        dserver = defer.Deferred()
        dclient = defer.Deferred()
        try:
            self.ssdp = reactor.listenMulticast(SSDP_PORT,
                                                ServerBase(self._node_id,
                                                           self._control_uri,
                                                           self.iface_send_list,
                                                           d=dserver
                                                          ),
                                                listenMultiple=True)
            self.ssdp.setTTL(5)
            for iface_ in self.iface_send_list:
                d = self.ssdp.joinGroup(SSDP_ADDR, interface=iface_)
                d.addErrback(lambda x: _log.error("Failed to join multicast group %s:%s, %s", iface_, SSDP_PORT, x))
                d.addCallback(lambda x: _log.debug("Joined multicast group %s:%s, %s", iface_, SSDP_PORT, x))
        except:
            _log.exception("Multicast listen join failed!!")
            # Dont start server some one is alerady running locally

        # TODO: Do we need this ?
        self.port = reactor.listenMulticast(0, ClientBase(dclient=dclient), interface=self.iface)
        _log.debug("SSDP Host: %s" % repr(self.port.getHost()))

        # Set ignore port and ips
        if self.ssdp and self.ignore_self:
            self.ssdp.protocol.set_ignore_list([(x, self.port.getHost().port) for x in self.iface_send_list])

        return dserver, dclient

    def update_server_params(self, service_uuid, **kwargs):
        self.ssdp.protocol.update_params(service_uuid, **kwargs)

    def start_search(self, service_uuid, **kwargs):
        callback = kwargs.pop('callback', None)
        stop = kwargs.pop('stop', False)
        # Restart backoff
        self.searches.setdefault(service_uuid, {})["backoff"] = .2

        def local_start_msearch():
            self.port.protocol.set_callback(service_uuid, callback)
            self.port.protocol.set_autostop(service_uuid, stop)
            self._send_msearch(service_uuid, once=False, kwargs=kwargs)

        reactor.callLater(0, local_start_msearch)

    def stop_all_search(self):
        for service_uuid in MS.keys():
            self.port.protocol.set_callback(service_uuid, None)
            self.port.protocol.stop(service_uuid)

    def stop_search(self, service_uuid):
        _log.debug("Stop search of %s" % service_uuid)
        self.port.protocol.set_callback(service_uuid, None)
        self.port.protocol.stop(service_uuid)

    def set_client_filter(self, service):
        self.port.protocol.set_service(service)

    def register_service(self, service, ip, port):
        self.ssdp.protocol.add_service(service, ip, port)

    def unregister_service(self, service):
        self.ssdp.protocol.remove_service(service)

    def _send_msearch(self, service_uuid, once=True, kwargs=None):
        if kwargs is None:
            kwargs={}
        if self.port and not self.port.protocol.is_stopped(service_uuid):
            for src_ip in self.iface_send_list:
                self.port.protocol.transport.setOutgoingInterface(src_ip)
                _log.debug("Sending  M-SEARCH... on %s\n%s" % (src_ip, MS[service_uuid].format(**kwargs)))
                self.port.write(MS[service_uuid].format(**kwargs), (SSDP_ADDR, SSDP_PORT))

            if not once and not self.port.protocol.is_stopped(service_uuid):
                reactor.callLater(self.searches[service_uuid]["backoff"], self._send_msearch,
                                    service_uuid, once=False, kwargs=kwargs)
                _log.debug("Next M-SEARCH in %s seconds" % self.searches[service_uuid]["backoff"])
                self.searches[service_uuid]["backoff"] = min(600, self.searches[service_uuid]["backoff"] * 1.5)

    def search(self, service_uuid, callback, **kwargs):
        self.port.protocol.set_callback(service_uuid, callback)
        self._send_msearch(service_uuid, once=True, kwargs=kwargs)

    def stop(self):
        dlist = []
        if self.ssdp:
            dlist.append(self.ssdp.leaveGroup(SSDP_ADDR, interface=self.iface))
            dlist.append(self.ssdp.stopListening())
            self.ssdp = None
        if self.port:
            self.stop_all_search()
            dlist.append(self.port.stopListening())
            self.port = None
        return defer.DeferredList(dlist)
