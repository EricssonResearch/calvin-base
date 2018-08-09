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

import pytest
import sys
import os
import traceback

import twisted

from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger

from calvin.runtime.south.storage.twistedimpl.dht.dht_server import *
from calvin.runtime.south.storage.twistedimpl.dht.service_discovery_ssdp import *

from calvin.runtime.south.async import threads

_log = calvinlogger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    def fin():
        reactor.callFromThread(reactor.stop)
    request.addfinalizer(fin)

@pytest.mark.slow
class TestDHT(object):
    test_nodes = 2
    _sucess_start = (True,)

    @pytest.inlineCallbacks
    def atest_dht_single(self, monkeypatch):
        from twisted.python import log

        log.startLogging(sys.stdout)
        iface = "0.0.0.0"
        a = None
        b = None
        q = Queue.Queue()

        defer.setDebugging(True)

        def server_started(a, *args):
            for b in args:
                if isinstance(b, twisted.python.failure.Failure):
                    b.printTraceback()
                else:
                    _log.debug("** %s" % b)
            q.put([a, args])

        try:
            a = AutoDHTServer()
            a.start(iface, cb=CalvinCB(server_started, "1"))

            # Wait for start
            assert q.get(timeout=2) == ["1", self._sucess_start]

            assert a.set(key="APA", value="banan").wait() == True
            assert a.get(key="APA").wait() == "banan"

        except Exception as e:
            _log.exception("Failed")
            pytest.fail(traceback.format_exc())
        finally:
            if a:
                yield threads.defer_to_thread(a.stop)

    @pytest.inlineCallbacks
    def test_dht_multi(self, monkeypatch):
        iface = "0.0.0.0"
        a = None
        b = None
        q = Queue.Queue()

        def server_started(aa, *args):
            for b in args:
                if isinstance(b, twisted.python.failure.Failure):
                    b.printTraceback()
                else:
                    _log.debug("** %s" % b)
            q.put([aa,args])

        try:
            amount_of_servers = 3
            a = AutoDHTServer()
            d = a.start(iface, cb=CalvinCB(server_started, "1"))

            b = AutoDHTServer()
            d = b.start(iface, cb=CalvinCB(server_started, "2"))

            c = AutoDHTServer()
            c.start(iface, cb=CalvinCB(server_started, "3"))

            # Wait for start
            servers = []
            while servers.__len__() < amount_of_servers:
	        try:
                    server = yield threads.defer_to_thread(q.get, timeout=2)
                except Queue.Empty:
                    _log.debug("Queue empty!")
                    break
                if server not in servers:
                    servers.append(server)
                    _log.debug("DHT Servers added: {}".format(servers))
                else:
                    _log.debug("Server: {} already started.".format(server))

            for server in range(1, amount_of_servers + 1):
                assert [str(server), self._sucess_start] in servers

            yield threads.defer_to_thread(time.sleep, 1)

            set_def = a.set(key="APA", value="banan")
            set_value = yield threads.defer_to_thread(set_def.wait)
            assert set_value

            get_def = a.get(key="APA")
            get_value = yield threads.defer_to_thread(get_def.wait)
            assert get_value == "banan"

            yield threads.defer_to_thread(time.sleep, .5)

            get_def = b.get(key="APA")
            get_value = yield threads.defer_to_thread(get_def.wait)
            assert get_value == "banan"

        except Exception as e:
            traceback.print_exc()
            pytest.fail(traceback.format_exc())
        finally:
            if a:
                a.stop()
            if b:
                b.stop()
            if c:
                c.stop()
            yield threads.defer_to_thread(time.sleep, 1)

    @pytest.inlineCallbacks
    def test_service_discovery(self, monkeypatch):
        q = Queue.Queue()

        def callback(addrs):
            _log.debug("Callback discovery got %s" % addrs)
            q.put(addrs)

        iface = "0.0.0.0"
        network = "test_super_network"

        ip = "192.168.199.199"
        port = 80

        _sd = SSDPServiceDiscovery(iface, ignore_self=False)
        server, client = _sd.start()

        _sd.register_service(network, ip, port)

        yield threads.defer_to_thread(time.sleep, .2)
        _sd.start_search(callback, stop=True)

        try:
            services = yield threads.defer_to_thread(q.get, timeout=4)
            assert ("192.168.199.199", 80) in services
        except:
            traceback.print_exc()
            assert False

        _sd.stop()
        #yield threads.defer_to_thread(_sd.stop)

    @pytest.inlineCallbacks
    def test_service_discovery_ignore(self, monkeypatch):
        q = Queue.Queue()

        def callback(addrs):
            _log.debug("Callback discovery got %s" % addrs)
            q.put(addrs)

        iface = "0.0.0.0"
        network = "test_super_network"

        ip = "192.168.199.199"
        port = 80

        _sd = SSDPServiceDiscovery(iface)
        server, client = _sd.start()

        _sd.register_service(network, ip, port)

        yield threads.defer_to_thread(time.sleep, .2)
        _sd.start_search(callback, stop=True)

        try:
            services = yield threads.defer_to_thread(q.get, timeout=4)
            assert False
        except:
            pass

        _sd.stop()
        #yield threads.defer_to_thread(_sd.stop)

    @pytest.inlineCallbacks
    def test_service_discovery_filter(self, monkeypatch):
        q = Queue.Queue()

        def callback_filter(addrs):
            _log.debug("Callback filter got %s" % addrs)
            q.put(addrs)

        iface = "0.0.0.0"
        network = "test_super_network"
        ip = "192.168.199.200"
        port = 80

        _sd = SSDPServiceDiscovery(iface, ignore_self=False)
        _sd.start()
        _sd.register_service("APA", ip, port)
        _sd.set_client_filter("BANAN")

        yield threads.defer_to_thread(time.sleep, .2)

        _sd.start_search(callback_filter, stop=True)

        try:
            services = yield threads.defer_to_thread(q.get, timeout=.5)
            assert False
        except:
            pass

        _sd.stop_search()

        def callback_filter_get(addrs):
            _log.debug("Callback filter got %s" % addrs)
            q.put(addrs)

        _sd.set_client_filter("APA")
        _sd.start_search(callback_filter_get, stop=True)

        try:
            services = yield threads.defer_to_thread(q.get, timeout=4)
            assert ("192.168.199.200", 80) in services
        except:
            traceback.print_exc()
            assert False

        _sd.stop()
        #yield threads.defer_to_thread(_sd.stop)

    @pytest.inlineCallbacks
    def test_callback(self, monkeypatch):
        from twisted.python import log
        log.startLogging(sys.stdout)

        iface = "0.0.0.0"
        a = None
        b = None
        q = Queue.Queue()

        def server_started(aa, *args):
            for b in args:
                if isinstance(b, twisted.python.failure.Failure):
                    b.printTraceback()
                else:
                    _log.debug("** %s" % b)
            q.put([aa,args])

        def set_cb(*args):
            _log.debug("** %s" % repr(args))
            q.put(args)

        def get_cb(*args):
            _log.debug("** %s" % repr(args))
            q.put(args)

        try:
            amount_of_servers = 3
            a = AutoDHTServer()
            a.start(iface, cb=CalvinCB(server_started, "1"))

            b = AutoDHTServer()
            b.start(iface, cb=CalvinCB(server_started, "2"))

            c = AutoDHTServer()
            c.start(iface, cb=CalvinCB(server_started, "3"))

            servers = []
            while servers.__len__() < amount_of_servers:
                try:
                    server = yield threads.defer_to_thread(q.get, timeout=2)
                except Queue.Empty:
                    _log.debug("Queue empty!")
                    break
                if server not in servers:
                    servers.append(server)
                    _log.debug("Servers added: {}.".format(servers))
                else:
                    _log.debug("Server: {} already started.".format(server))

            for server in range(1, amount_of_servers + 1):
                assert [str(server), self._sucess_start] in servers

            yield threads.defer_to_thread(time.sleep, 1)
            yield threads.defer_to_thread(q.queue.clear)

            a.set(key="APA", value="banan", cb=CalvinCB(set_cb))
            set_value = yield threads.defer_to_thread(q.get, timeout=2)
            assert ("APA", True) == set_value

            yield threads.defer_to_thread(time.sleep, 1)
            yield threads.defer_to_thread(q.queue.clear)

            a.get(key="APA", cb=CalvinCB(get_cb))
            get_value = yield threads.defer_to_thread(q.get, timeout=2)
            assert get_value == ("APA", "banan")

            yield threads.defer_to_thread(time.sleep, 1)
            yield threads.defer_to_thread(q.queue.clear)

            b.get(key="APA", cb=CalvinCB(get_cb))
            get_value = yield threads.defer_to_thread(q.get, timeout=2)
            assert get_value == ("APA", "banan")

        except Exception as e:
            _log.exception("Failed")
            pytest.fail(traceback.format_exc())
        finally:
            if a:
                a.stop()
            if b:
                b.stop()
            if c:
                c.stop()
            yield threads.defer_to_thread(time.sleep, 1)

