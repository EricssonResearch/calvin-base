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
from calvin.utilities import certificate
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger
from calvin.utilities.utils import get_home
from calvin.utilities import runtime_credentials
from calvin.runtime.south.storage.twistedimpl.securedht.append_server import *
from calvin.runtime.south.storage.twistedimpl.securedht.dht_server import *
from calvin.runtime.south.storage.twistedimpl.securedht.service_discovery_ssdp import *
from calvin.runtime.south.storage.twistedimpl.securedht.dht_server_commons import drawNetworkState
from kademlia.node import Node
from kademlia.utils import deferredDict, digest

from calvin.runtime.south.async import threads
from calvin.utilities import calvinconfig
import socket
from calvin.tests.helpers import get_ip_addr
ip_addr = get_ip_addr()

_log = calvinlogger.get_logger(__name__)
name = "node3:"
homefolder = get_home()
domain = "sec-dht-security-test"
testdir = os.path.join(homefolder, ".calvin","sec_dht_security_test")
configdir = os.path.join(testdir, domain)
runtimesdir = os.path.join(testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")

_conf = calvinconfig.get()
_conf.add_section("security")
_conf.set('security', "runtimes_path", runtimesdir)
_conf.set('security', "domain_name", domain)
_conf.set('security', "security_path",testdir)

@pytest.fixture(scope="session", autouse=True)


def cleanup(request):
    def fin():
        reactor.callFromThread(reactor.stop)
    request.addfinalizer(fin)

@pytest.mark.slow
class TestDHT(object):
    test_nodes = 2
    _sucess_start = (True,)

    @pytest.fixture(autouse=True, scope="class")
    def setup(self, request):
        pass

    @pytest.inlineCallbacks
    def test_dht_multi(self, monkeypatch):
        iface = "0.0.0.0"
        a = None
        b = None
        q = Queue.Queue()
        rt_credentials=[]


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
                uri="http://{}:500{}".format(ip_addr, servno)
                control_uri="http://{}:502{}".format(ip_addr, servno)
                rt_cred = runtime_credentials.RuntimeCredentials(name=name+str(servno), domain=domain,security_dir=testdir)
                rt_credentials.append(rt_cred)
                node_id = rt_cred.node_id
                a = AutoDHTServer(node_id, control_uri, rt_cred)
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
                    _log.debug("DHT Servers added: {}".format(started))
                    callbacks[int(server[0][0])].func = lambda *args, **kvargs:None
                else:
                    _log.debug("Server: {} already started." \
                               " {} out of {}".format(started,
                                                     len(started),
                                                     amount_of_servers))

            _log.debug("All {} out of {} started".format(started,
                                                     len(started),
                                                     amount_of_servers))
            for servno in range(0, amount_of_servers):
                assert [str(servno), self._sucess_start] in started

            yield threads.defer_to_thread(q.queue.clear)
            yield threads.defer_to_thread(time.sleep, 8)

            key = "KOALA"
            value = "bambu"
            set_def = servers[0].set(key=key, value=value)
            set_value = yield threads.defer_to_thread(set_def.wait, 10)
            assert set_value
            print("Node with port {} posted key={}, value={}".format(servers[0].dht_server.port.getHost().port, key, value))
            get_def = servers[0].get(key="KOALA")
            get_value = yield threads.defer_to_thread(get_def.wait, 10)
            assert get_value == "bambu"
            print("Node with port {} confirmed key={}, value={} was reachable".format(servers[0].dht_server.port.getHost().port, key, value))

            drawNetworkState("3nice_graph.png", servers, amount_of_servers)
            yield threads.defer_to_thread(time.sleep, 7)
            drawNetworkState("3middle_graph.png", servers, amount_of_servers)
            yield threads.defer_to_thread(time.sleep, 7)
            drawNetworkState("3end_graph.png", servers, amount_of_servers)

            get_def = servers[0].get(key="KOALA")
            get_value = yield threads.defer_to_thread(get_def.wait, 10)
            assert get_value == "bambu"
            print("Node with port {} got right value: {}".format(servers[0].dht_server.port.getHost().port, get_value))
            for i in range(0, amount_of_servers):
                name_dir = rt_credentials[i].get_credentials_path()
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
            for server in servers:
                server.stop()
