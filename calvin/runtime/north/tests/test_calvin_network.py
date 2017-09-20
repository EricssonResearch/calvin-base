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
import random
import time
import json
import uuid
import Queue
import multiprocessing
import traceback

from calvin.utilities import calvinlogger
from calvin.utilities.calvin_callback import CalvinCB, CalvinCBClass
from mock import Mock, MagicMock
from calvin.runtime.north.calvin_network import CalvinNetwork
from twisted.internet import reactor, defer, threads
from calvin.runtime.north import storage
from calvin.utilities import calvinconfig
from calvin.runtime.north.plugins.storage import storage_factory
from calvin.tests.helpers_twisted import create_callback
import calvin.tests

_conf = calvinconfig.get()
_log = calvinlogger.get_logger(__name__)

def snoop_f(_object):

    new_object = MagicMock(wraps=_object)

    d = defer.Deferred()

    new_object.side_effect_ds = []
    new_object.side_effect_ds.append(d)

    def _dummy(*args, **kwargs):
        new_object.side_effect_ds[0].callback((args, kwargs))
        new_d = defer.Deferred()
        new_object.side_effect_ds.insert(0, new_d)

    new_object.side_effect = _dummy
    return new_object

def __set_uris(self, uris, i, ext_control_uris=None):
    self.uris = uris
    self.external_control_uri = ext_control_uris or uris[i]

def create_node(global_storage):
    node = calvin.tests.TestNode([""])
    node._set_uris = __set_uris
    #node = MagicMock()
    #node.id = str(uuid.uuid4())
    #node.name = node.id
    node.storage = storage.Storage(node, override_storage=global_storage)
    #node = calvin.tests.TestNode("127.0.0.1:5000")
    # Delay this until started, when we have a port and so on.
    #node.storage.add_node(node)

    return node

"""
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    def fin():
        reactor.callFromThread(reactor.stop)
    request.addfinalizer(fin)
    print "hejsan"
"""

# So it skipps if we dont have twisted plugin
def _dummy_inline(*args):
    pass

if not hasattr(pytest, 'inlineCallbacks'):
    pytest.inlineCallbacks = _dummy_inline

@pytest.mark.skipif(pytest.inlineCallbacks == _dummy_inline,
                    reason="No inline twisted plugin enabled, please use --twisted to py.test")
class TestCalvinNetwork(object):

    def _get_port(self, no):
        return self._ports[no]

    def _get_network(self, no):
        return self._networks[no]

    def _get_node_id(self, no):
        return self._networks[no].node.id

    @pytest.inlineCallbacks
    def _create_servers(self, count, extra_uris=None):
        #import logging
        #calvinlogger.get_logger().setLevel(logging.DEBUG)
        #calvinlogger.get_logger().setLevel(1)

        if hasattr(self, '_networks') and self._networks:
            raise Exception("Trying to create multiple times without stop!")

        if not extra_uris:
            extra_uris = []

        self._networks = []
        self._ports = []
        _conf.set('global', 'storage_type', 'test_local')
        #_conf.set('global', 'storage_proxy', 'local')
        global_storage = storage_factory.get("test_local", None)

        for a in range(count):
            node1 = create_node(global_storage)
            network1 = CalvinNetwork(node1)

            cb, d = create_callback()
            node1.storage.start(cb=cb)
            res = yield d
            assert res[0][0]

            for fname in ['_join_finished', '_join_failed', '_server_started', '_server_stopped', '_recv_handler', '_peer_connection_failed', '_peer_disconnected']:
                _o = getattr(network1, fname)
                setattr(network1, fname, snoop_f(_o))
            assert network1._server_started.call_count == 0

            network1.register(['calvinip'], ['json'])
            network1.start_listeners()

            # Wait for everything to settle
            start = network1._server_started.side_effect_ds[-1]
            yield start

            #yield threads.deferToThread(time.sleep, .05)
            assert network1._server_started.call_count == 1

            # get listening ports
            net1_port = network1._server_started.call_args[0][1]
            node1._set_uris(node1, extra_uris + ["calvinip://127.0.0.1:%s" % net1_port], -1)
            cb, d = create_callback()
            node1.storage.add_node(node1, cb=CalvinCB(cb))
            res = yield d
            assert res[1]['value']
            self._networks.append(network1)
            self._ports.append(net1_port)

    @pytest.inlineCallbacks
    def _stop_servers(self, no=None, remove=True):
        if no is None:
            for net in self._networks:
                net.stop_listeners()
                # Wait for everything to be done
                stopped = net._server_stopped.side_effect_ds[0]
                yield stopped
                #yield threads.deferToThread(time.sleep, .05)
                assert net._server_stopped.call_count == 1
            if remove:
                del self._networks
                del self._ports
        else:
            net = self._networks[no]
            #yield threads.deferToThread(time.sleep, .05)
            stopped = network1._server_started.side_effect_ds[0]
            yield stopped
            assert net._server_stopped.call_count == 1
            if remove:
                del self._networks[no]
                del self._ports[no]

    @pytest.inlineCallbacks
    def test_start_stop(self, monkeypatch):
        yield self._create_servers(2)
        yield threads.deferToThread(time.sleep, .01)
        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_connect(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        self._get_network(0).join(["calvinip://127.0.0.1:%s" % net1_port], cb)
        b = yield d
        print b[1]
        assert b[1]['status']

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_connect_disconnect(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        self._get_network(0).join(["calvinip://127.0.0.1:%s" % net1_port], cb)
        b = yield d
        print b[1]
        assert b[1]['status']

        self._get_network(0).link_get(b[1]['peer_node_id']).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_connect_disconnect_bad(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        self._get_network(0).join(["calvinip://127.0.0.1:%s" % net1_port], cb)
        b = yield d
        print b[1]
        assert b[1]['status']

        self._get_network(0).link_get(b[1]['peer_node_id']).transport._transport._proto.transport.abortConnection()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason ERROR
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "ERROR"

        yield self._stop_servers()


    @pytest.inlineCallbacks
    def test_connect_failed(self, monkeypatch):
        yield self._create_servers(2)
        cb, d = create_callback()
        #network1.join(["calvinip://127.0.0.1:%s" % net2_port], cb)
        self._get_network(0).join(["calvinip://127.0.0.1:12345"], cb)
        b = yield d
        print b[1]
        assert not b[1]['status']

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_reconnect_failed(self, monkeypatch):
        yield self._create_servers(2)

        # Connect
        """
        cb, d = create_callback()
        net1_port = self._get_port(1)
        self._get_network(0).join(["calvinip://127.0.0.1:%s" % net1_port], cb)
        b = yield d
        print b[1]['status']
        assert b[1]['status']
        """
        # kill the connection permanently, stopping the server

        # Check that it died, and reconnect dont occur

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_reconnect(self, monkeypatch):
        yield self._create_servers(2)

        # Connect
        """
        cb, d = create_callback()
        net1_port = self._get_port(1)
        self._get_network(0).join(["calvinip://127.0.0.1:%s" % net1_port], cb)
        b = yield d
        print b[1]
        assert b[1]['status']

        # kill the connection
        self._get_network(0).link_get(b[1]['peer_node_id']).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        # Check that its alive again, wait for join
        """

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request(self, monkeypatch):
        #import sys
        #from twisted.python import log
        #log.startLogging(sys.stdout)
        #defer.setDebugging(True)
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_dual(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        cb2, d2 = create_callback()
        self._get_network(0).link_request(node_id, callback=cb)
        self._get_network(0).link_request(node_id, callback=cb2)
        b = yield d
        print b
        assert b[1]['status']
        b2 = yield d2
        print b2
        assert b2[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_hot_cache(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        # All done, just a get from cache
        cb, d = create_callback()
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_cold_cache(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        self._get_network(0).link_get(b[0][0]).close()
        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        # All done, just a get from cache
        cb, d = create_callback()
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 2
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_cache_old(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        cb, d = create_callback()

        # may fail if someone is listening :)
        self._get_network(0)._peer_cache[b[0][0]]['uris'] = ['calvinip://127.0.0.1:12345']
        self._get_network(0)._peer_cache[b[0][0]]['timestamp'] = time.time() - 30*60
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 2
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_cache_old_dual(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        cb, d = create_callback()
        cb2, d2 = create_callback()

        # may fail if someone is listening :)
        self._get_network(0)._peer_cache[b[0][0]]['uris'] = ['calvinip://127.0.0.1:12345']
        self._get_network(0)._peer_cache[b[0][0]]['timestamp'] = time.time() - 30*60
        self._get_network(0).link_request(node_id, callback=cb)
        self._get_network(0).link_request(node_id, callback=cb2)
        b = yield d
        print b
        assert b[1]['status']
        b = yield d2
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 2
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_cache_fail(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        assert self._get_network(0)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(0)._peer_disconnected.call_args[0][2] == "OK"

        cb, d = create_callback()
        cb2, d2 = create_callback()

        # may fail if someone is listening :)
        self._get_network(0)._peer_cache[b[0][0]]['uris'] = ['calvinip://127.0.0.1:12345']
        self._get_network(0).link_request(node_id, callback=cb)
        self._get_network(0).link_request(node_id, callback=cb2)

        # Should fail cache is new but addr is wrong
        b = yield d
        print b
        assert not b[1]['status']
        b = yield d2
        print b
        assert not b[1]['status']

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_cache_fail_multiple(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        assert self._get_network(0)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(0)._peer_disconnected.call_args[0][2] == "OK"

        cb, d = create_callback()
        cb2, d2 = create_callback()

        # may fail if someone is listening :)
        self._get_network(0)._peer_cache[b[0][0]]['uris'] = ['calvinip://127.0.0.1:12345',
                                                             'calvinip://127.0.0.1:12346', 
                                                             'calvinip://127.0.0.1:12347']
        self._get_network(0).link_request(node_id, callback=cb)
        self._get_network(0).link_request(node_id, callback=cb2)

        # Should fail cache is new but addr is wrong
        b = yield d
        print b
        assert not b[1]['status']
        b = yield d2
        print b
        assert not b[1]['status']

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_cache_fail_multiple(self, monkeypatch):
        yield self._create_servers(2)
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        self._get_network(0).link_request(node_id, callback=cb)
        b = yield d
        print b
        assert b[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        assert self._get_network(0)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(0)._peer_disconnected.call_args[0][2] == "OK"

        cb, d = create_callback()
        cb2, d2 = create_callback()

        # may fail if someone is listening :)
        self._get_network(0)._peer_cache[b[0][0]]['uris'] = ['calvinip://127.0.0.1:12345',
                                                             'calvinip://127.0.0.1:12346', 
                                                             'calvinip://127.0.0.1:12347']
        self._get_network(0)._peer_cache[b[0][0]]['timestamp'] = time.time() - 30*60
        self._get_network(0).link_request(node_id, callback=cb)
        self._get_network(0).link_request(node_id, callback=cb2)

        # Should fail cache is new but addr is wrong
        b = yield d
        print b[1]
        assert b[1]['status']
        b = yield d2
        print b[1]
        assert b[1]['status']

        yield self._stop_servers()

    @pytest.inlineCallbacks
    def test_link_request_one_fail(self, monkeypatch):
        yield self._create_servers(2, extra_uris=['calvinip://127.0.0.1:12345'])
        # Connect
        cb, d = create_callback()
        net1_port = self._get_port(1)
        node_id = self._get_node_id(1)
        cb2, d2 = create_callback()
        self._get_network(0).link_request(node_id, callback=cb)
        self._get_network(0).link_request(node_id, callback=cb2)
        b = yield d
        print b[1]
        assert b[1]['status']
        b2 = yield d2
        print b2[1]
        assert b2[1]['status']

        assert self._get_network(0).link_get(b[0][0])
        self._get_network(0).link_get(b[0][0]).close()

        disconnect = self._get_network(1)._peer_disconnected.side_effect_ds[0]
        yield disconnect
        assert self._get_network(1)._peer_disconnected.call_count == 1
        # reason OK
        assert self._get_network(1)._peer_disconnected.call_args[0][2] == "OK"

        yield self._stop_servers()

