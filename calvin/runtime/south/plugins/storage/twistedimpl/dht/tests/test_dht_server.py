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

from calvin.runtime.south.plugins.storage.twistedimpl.dht.dht_server import *
from calvin.runtime.south.plugins.storage.twistedimpl.dht.service_discovery_ssdp import *

_log = calvinlogger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    def fin():
        reactor.callFromThread(reactor.stop)
    request.addfinalizer(fin)

@pytest.mark.interactive
@pytest.mark.slow
class TestDHT(object):
    test_nodes = 2
    _sucess_start = (True,)

    def test_dht_single(self, monkeypatch):
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
                a.stop()

    def test_dht_multi(self, monkeypatch):
        iface = "0.0.0.0"
        a = None
        b = None
        q = Queue.Queue()

        def server_started(a, *args):
            for b in args:
                if isinstance(b, twisted.python.failure.Failure):
                    b.printTraceback()
                else:
                    _log.debug("** %s" % b)
            q.put([a,args])

        try:
            a = AutoDHTServer()
            a.start(iface, cb=CalvinCB(server_started, "1"))

            b = AutoDHTServer()
            b.start(iface, cb=CalvinCB(server_started, "2"))

            # Wait for start
            servers = [q.get(timeout=2), q.get(timeout=2)]
            _log.debug("** servers %s" % repr(servers))
            assert ["1", self._sucess_start] in servers
            assert ["2", self._sucess_start] in servers

            assert a.set(key="APA", value="banan").wait()
            assert a.get(key="APA").wait() == "banan"

            time.sleep(.5)
            assert b.get(key="APA").wait() == "banan"

        except Exception as e:
            traceback.print_exc()
            pytest.fail(traceback.format_exc())
        finally:
            if a:
                a.stop()
            if b:
                b.stop()

    def test_service_discovery(self, monkeypatch):
        q = Queue.Queue()

        def callback(addrs):
            _log.debug("Callback discovery got %s" % addrs)
            q.put(addrs)

        iface = "0.0.0.0"
        network = "test_super_network"

        ip = "192.168.199.199"
        port = 80

        _sd = ThreadWrapper(SSDPServiceDiscovery, iface)
        _sd.start()
        _sd.register_service(network, ip, port)
        _sd.start_search(callback, stop=True)
        try:
            assert ("192.168.199.199", 80) in q.get(timeout=2)
        except:
            traceback.print_exc()
            assert False
        _sd.stop()

    def test_service_discovery_filter(self, monkeypatch):
        q = Queue.Queue()

        def callback_filter(addrs):
            _log.debug("Callback filter got %s" % addrs)
            q.put(addrs)

        iface = "0.0.0.0"
        network = "test_super_network"
        ip = "192.168.199.200"
        port = 80

        _sd = ThreadWrapper(SSDPServiceDiscovery, iface)
        _sd.start()
        _sd.register_service("APA", ip, port)
        _sd.set_client_filter("BANAN")
        _sd.start_search(callback_filter, stop=True)
        try:
            q.get(timeout=.5)
            assert False
        except:
            pass
        _sd.stop_search()

        q = Queue.Queue()

        def callback_filter_get(addrs):
            _log.debug("Callback filter got %s" % addrs)
            q.put(addrs)

        _sd.set_client_filter("APA")
        _sd.start_search(callback_filter_get, stop=True)
        try:
            assert ("192.168.199.200", 80) in q.get(timeout=2)
        except:
            _log.exception("The search had a timeout")
            assert False

        _sd.stop()

    def test_callback(self, monkeypatch):
        iface = "0.0.0.0"
        a = None
        b = None
        q = Queue.Queue()

        def server_started(a, *args):
            for b in args:
                if isinstance(b, twisted.python.failure.Failure):
                    b.printTraceback()
                else:
                    _log.debug("** %s" % b)
            q.put([a,args])

        def set_cb(*args):
            _log.debug("** %s" % repr(args))
            q.put(args)

        def get_cb(*args):
            _log.debug("** %s" % repr(args))
            q.put(args)

        try:
            a = AutoDHTServer()
            a.start(iface, cb=CalvinCB(server_started, "1"))

            b = AutoDHTServer()
            b.start(iface, cb=CalvinCB(server_started, "2"))

            # Wait for start
            servers = [q.get(timeout=2), q.get(timeout=2)]

            assert ["1", self._sucess_start] in servers
            assert ["2", self._sucess_start] in servers

            a.set(key="APA", value="banan", cb=CalvinCB(set_cb))

            assert q.get(timeout=2) == ("APA", True)

            a.get(key="APA", cb=CalvinCB(get_cb))

            assert q.get(timeout=2) == ("APA", "banan")

            time.sleep(.5)
            b.get(key="APA", cb=CalvinCB(get_cb))

            assert q.get(timeout=2) == ("APA", "banan")

        except Exception as e:
            _log.exception("Failed")
            pytest.fail(traceback.format_exc())
        finally:
            if a:
                a.stop()
            if b:
                b.stop()
