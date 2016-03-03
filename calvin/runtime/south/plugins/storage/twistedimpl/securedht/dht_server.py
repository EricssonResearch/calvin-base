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

import sys
import traceback
import time
import Queue
import os
import OpenSSL.crypto

from twisted.internet import reactor, defer, threads

from calvin.runtime.south.plugins.storage.twistedimpl.securedht.append_server import AppendServer
from calvin.runtime.south.plugins.storage.twistedimpl.securedht.service_discovery_ssdp import SSDPServiceDiscovery
from calvin.utilities import certificate
from calvin.runtime.north.plugins.storage.storage_base import StorageBase
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)


def logger(message):
    _log.debug(message)
    #print message


class ServerApp(object):

    def __init__(self, server_type, identifier):
        self.kserver = None
        self.port = None
        self.server_type = server_type
        self.id = identifier

    def start(self, port=0, iface='', bootstrap=None):
        if bootstrap is None:
            bootstrap = []

        self.kserver = self.server_type(id=self.id)
        self.kserver.bootstrap(bootstrap)

        self.port = reactor.listenUDP(port,
                                        self.kserver.protocol,
                                        interface=iface)

        return self.port.getHost().host, self.port.getHost().port

    def __getattr__(self, name):
        if hasattr(self.kserver, name) and callable(getattr(self.kserver, name)):
            return getattr(self.kserver, name)
        else:
            # Default behaviour
            raise AttributeError

    def get_port(self):
        return self.port

    def stop(self):
        if self.port:
            return self.port.stopListening()


class ThreadWrapper(object):
    def __init__(self, obj, *args, **kwargs):
        self._obj = threads.blockingCallFromThread(reactor, obj, *args, **kwargs)

    def _call(self, func, *args, **kwargs):
        return threads.blockingCallFromThread(reactor, func, *args, **kwargs)

    def __getattr__(self, name):
        class Caller(object):
            def __init__(self, f, func):
                self.f = f
                self.func = func

            def __call__(self, *args, **kwargs):
                # _log.debug("Calling %s(%s, %s, %s)" %(self.f, self.func, args,  kwargs))
                return self.func(*args, **kwargs)

        if hasattr(self._obj, name):
            if callable(getattr(self._obj, name)):
                return Caller(self._call, getattr(self._obj, name))
            else:
                return getattr(self._obj, name)

        else:
            # Default behaviour
            raise AttributeError


class TwistedWaitObject(object):
    def __init__(self, func, **kwargs):
        self._value = None
        self._q = Queue.Queue()
        self._done = False
        self._func = func
        self._kwargs = kwargs
        self._callback_class = kwargs.pop("cb")
        d = func(**kwargs)
        d.addCallback(self._callback)

    def _callback(self, value):
        self._value = value
        if self._callback_class:
            self._callback_class(self._kwargs['key'], value)
            # reactor.callFromThread(self._callback_class, self._kwargs['key'], value)
        self._q.put(self._value)
        self._done = True

    def done(self):
        return self._done

    def wait(self, timeout=5):
        if self.done():
            return self._value
        try:
            value = self._q.get(timeout=timeout)
        except Queue.Empty:
            logger("Timeout in %s(%s)" % (self._func, self._kwargs))
            raise
        return value

    def get(self):
        return self._value


class AutoDHTServer(StorageBase):
    def __init__(self):
        super(AutoDHTServer, self).__init__()
        self.dht_server = None
        self._ssdps = None
        self._started = False
        self.cert_conf = certificate.Config(_conf.get("security", "certificate_conf"),
                                            _conf.get("security", "certificate_domain")).configuration

    def start(self, iface='', network=None, bootstrap=None, cb=None, name=None):
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
            raise
        # Derive DHT node id
        key = cert.digest("sha256")
        newkey = key.replace(":", "")
        bytekey = newkey.decode("hex")

        if network is None:
            network = _conf.get_in_order("dht_network_filter", "ALL")

        self.dht_server = ServerApp(AppendServer, bytekey[-20:])
        ip, port = self.dht_server.start(iface=iface)

        dlist = []
        dlist.append(self.dht_server.bootstrap(bootstrap))

        self._ssdps = SSDPServiceDiscovery(iface, cert=certstr)
        dlist += self._ssdps.start()

        logger("Register service %s %s:%s" % (network, ip, port))
        self._ssdps.register_service(network, ip, port)

        logger("Set client filter %s" % (network))
        self._ssdps.set_client_filter(network)

        start_cb = defer.Deferred()

        def bootstrap_proxy(addrs):
            def started(args):
                logger("DHT Started %s" % (args))
                if not self._started:
                    reactor.callLater(.2, start_cb.callback, True)
                if cb:
                    reactor.callLater(.2, cb, True)
                self._started = True

            def failed(args):
                logger("DHT failed to bootstrap %s" % (args))
                #reactor.callLater(.5, bootstrap_proxy, addrs)

            logger("Trying to bootstrap with %s" % (repr(addrs)))
            d = self.dht_server.bootstrap(addrs)
            d.addCallback(started)
            d.addErrback(failed)

        def start_msearch(args):
            logger("** msearch %s args: %s" % (self, repr(args)))
            reactor.callLater(0,
                                self._ssdps.start_search,
                                bootstrap_proxy,
                                stop=False)

        # Wait until servers all listen
        dl = defer.DeferredList(dlist)
        dl.addBoth(start_msearch)
        # Only for logging
        self.dht_server.kserver.protocol.sourceNode.port = port
        self.dht_server.kserver.protocol.sourceNode.ip = "0.0.0.0"
        #FIXME handle inside ServerApp
        self.dht_server.kserver.name = name
        self.dht_server.kserver.protocol.name = name
        self.dht_server.kserver.protocol.storeOwnCert(certstr)
        self.dht_server.kserver.protocol.setPrivateKey()

        return start_cb

    def set(self, key, value, cb=None):
        return TwistedWaitObject(self.dht_server.set, key=key, value=value, cb=cb)

    def get(self, key, cb=None):
        return TwistedWaitObject(self.dht_server.get, key=key, cb=cb)

    def get_concat(self, key, cb=None):
        return TwistedWaitObject(self.dht_server.get_concat, key=key, cb=cb)

    def append(self, key, value, cb=None):
        return TwistedWaitObject(self.dht_server.append, key=key, value=value, cb=cb)

    def remove(self, key, value, cb=None):
        return TwistedWaitObject(self.dht_server.remove, key=key, value=value, cb=cb)

    def bootstrap(self, addrs, cb=None):
        return TwistedWaitObject(self.dht_server.bootstrap, addr=addrs, cb=cb)

    def stop_search(self):
        return self._ssdps.stop_search()

    def stop(self, cb=None):
        d1 = self.dht_server.stop()
        d2 = self._ssdps.stop()

        dl = defer.DeferredList((d1, d2))
        if cb:
            dl.addBoth(cb)

        return dl

def main(iface):
    ret = 0
    try:
        a = AutoDHTServer()
        a.start(iface)

        b = AutoDHTServer()
        b.start(iface)

        time.sleep(4)

        print a.set(key="APA", value="banan")

        print a.get(key="APA")
        print b.get(key="APA")

        a.stop()
        b.stop()

    except:
        traceback.print_exc()
        ret = 1

    finally:
        if reactor.running:
            threads.blockingCallFromThread(reactor, reactor.stop)

    return ret

if __name__ == "__main__":
    print sys.argv
    if len(sys.argv) != 2:
        print "Usage: %s <server|client> <IP of interface>" % (sys.argv[0], )
        # sys.exit(1)
        interface = ''
    else:
        interface = sys.argv[1]
    sys.exit(main(interface))
