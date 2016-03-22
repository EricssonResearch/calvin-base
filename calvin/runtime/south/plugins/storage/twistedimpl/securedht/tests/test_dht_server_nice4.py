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
import hashlib
import twisted
import shutil
import json

from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger
from calvin.utilities.utils import get_home
from calvin.runtime.south.plugins.storage.twistedimpl.securedht.append_server import *
from calvin.runtime.south.plugins.storage.twistedimpl.securedht.dht_server import *
from calvin.runtime.south.plugins.storage.twistedimpl.securedht.service_discovery_ssdp import *
from calvin.runtime.south.plugins.storage.twistedimpl.securedht.dht_server_commons import drawNetworkState
from kademlia.node import Node
from kademlia.utils import deferredDict, digest

from calvin.runtime.south.plugins.async import threads
from calvin.utilities import calvinconfig

_conf = calvinconfig.get()
_conf.add_section("security")
_conf_file = os.path.join(get_home(), ".calvin/security/test/openssl.conf")
_conf.set("security", "certificate_conf", _conf_file)
_conf.set("security", "certificate_domain", "test")
_cert_conf = None

_log = calvinlogger.get_logger(__name__)
name = "node4:"

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

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        global _cert_conf
        _cert_conf = certificate.Config(_conf_file, "test").configuration

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
            amount_of_servers = 5
            # Twisted is using 20 threads so having > 20 server
            # causes threadlocks really easily.

            servers = []
            callbacks = []
            for servno in range(0, amount_of_servers):
                a = AutoDHTServer()
                servers.append(a)
                callback = CalvinCB(server_started, str(servno))
                servers[servno].start(iface, network="Niklas", cb=callback, name=name + "{}".format(servno))
                callbacks.append(callback)
                
            # Wait for start
            started = []
            while len(started) < amount_of_servers:
                try:
                    server = yield threads.defer_to_thread(q.get)
                except Queue.Empty:
                    _log.debug("Queue empty!")
                    #raise    
                if server not in started:
                    started.append(server)
                    #print("DHT Servers added: {}".format(started))
                    callbacks[int(server[0][0])].func = lambda *args, **kvargs:None
                else:
                    print("Server: {} already started." \
                               " {} out of {}".format(started,
                                                     len(started),
                                                     amount_of_servers))

            print("All {} out of {} started".format(started,
                                                     len(started),
                                                     amount_of_servers))
            for servno in range(0, amount_of_servers):
                assert [str(servno), self._sucess_start] in started
            
            yield threads.defer_to_thread(q.queue.clear)
            yield threads.defer_to_thread(time.sleep, 8)

            key = "HARE"
            value = json.dumps(["morot"])
            set_def = servers[0].append(key=key, value=value)
            set_value = yield threads.defer_to_thread(set_def.wait, 10)
            assert set_value
            print("Node with port {} posted append key={}, value={}".format(servers[0].dht_server.port.getHost().port, key, value))
            value = json.dumps(["selleri"])
            set_def = servers[0].append(key=key, value=value)
            set_value = yield threads.defer_to_thread(set_def.wait, 10)
            assert set_value
            print("Node with port {} posted append key={}, value={}".format(servers[0].dht_server.port.getHost().port, key, value))
            get_def = servers[0].get_concat(key=key)
            get_value = yield threads.defer_to_thread(get_def.wait, 10)
            assert set(json.loads(get_value)) == set(["morot", "selleri"])
            print("Node with port {} confirmed key={}, value={} was reachable".format(servers[0].dht_server.port.getHost().port, key, get_value))

            drawNetworkState("1nice_graph.png", servers, amount_of_servers)
            yield threads.defer_to_thread(time.sleep, 7)
            drawNetworkState("1middle_graph.png", servers, amount_of_servers)
            yield threads.defer_to_thread(time.sleep, 7)
            drawNetworkState("1end_graph.png", servers, amount_of_servers)

            get_def = servers[0].get_concat(key=key)
            get_value = yield threads.defer_to_thread(get_def.wait, 10)
            assert set(json.loads(get_value)) == set(["morot", "selleri"])
            print("Node with port {} got right value: {}".format(servers[0].dht_server.port.getHost().port, get_value))
            value = json.dumps(["morot"])
            set_def = servers[0].remove(key=key, value=value)
            set_value = yield threads.defer_to_thread(set_def.wait, 10)
            assert set_value
            print("Node with port {} posted remove key={}, value={}".format(servers[0].dht_server.port.getHost().port, key, value))
            get_def = servers[1].get_concat(key=key)
            get_value = yield threads.defer_to_thread(get_def.wait, 10)
            assert set(json.loads(get_value)) == set(["selleri"])
            print("Node with port {} got right value: {}".format(servers[0].dht_server.port.getHost().port, get_value))
            for i in range(0, amount_of_servers):
                name_dir = os.path.join(_cert_conf["CA_default"]["runtimes_dir"], "{}{}".format(name, i))
                filenames = os.listdir(os.path.join(name_dir, "others"))
                print("Node with port {} has {} certificates in store".format(servers[i].dht_server.port.getHost().port, len(filenames)))

        except AssertionError as e:
            print("Node with port {} got wrong value: {}, should have been {}".format(servers[0].dht_server.port.getHost().port, get_value, value))
            pytest.fail(traceback.format_exc())
        except Exception as e:
            traceback.print_exc()
            pytest.fail(traceback.format_exc())
        finally:
            yield threads.defer_to_thread(time.sleep, 10)
            i = 0
            for server in servers:
                name_dir = os.path.join(_cert_conf["CA_default"]["runtimes_dir"], name + "{}".format(i))
                shutil.rmtree(os.path.join(name_dir, "others"), ignore_errors=True)
                os.mkdir(os.path.join(name_dir, "others"))
                i += 1
                server.stop()
