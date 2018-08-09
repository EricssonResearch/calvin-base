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
import random
import time
import json
import Queue

from twisted.application import service, internet
from twisted.python.log import ILogObserver
from twisted.internet import reactor, task, defer, threads
from threading import Thread
from kademlia import log

from calvin.runtime.south.storage.twistedimpl.securedht.append_server import AppendServer


# _log = get_logger(__name__)

class KNet(object):

    def __init__(self, number, server_type=AppendServer):
        self.nodes = []
        self.boot_strap = None

        if not reactor.running:
            print "Starting reactor only once"
            self.reactor_thread = Thread(target=reactor.run, args=(False,)).start()

        for a in xrange(number):
            self.nodes.append(ServerApp(server_type))


    def start(self):
        bootstrap = []
        for a in self.nodes:
            port, kserver = a.start(0, bootstrap)
            if len(bootstrap) < 100:
                bootstrap.append(("127.0.0.1", port))

        # Wait for them to start
        time.sleep(.8)

    def stop(self):
        for node in self.nodes:
            node.stop()
        self.nodes = []
        time.sleep(1)

    def get_rand_node(self):
        index = random.randint(0, max(0, len(self.nodes) - 1))
        return self.nodes[index]


class ServerApp(object):

    def __init__(self, server_type):
        self.server_type = server_type

    def start(self, port=0, boot_strap=[]):
        self.kserver = self.server_type()
        self.kserver.bootstrap(boot_strap)

        self.port = threads.blockingCallFromThread(reactor, reactor.listenUDP, port, self.kserver.protocol)
        print "Starting server:", self.port

        time.sleep(.2)

        return self.port.getHost().port, self.kserver

    def call(self, func, *args, **kwargs):
        reactor.callFromThread(func, *args, **kwargs)

    def __getattr__(self, name):
        class caller:
            def __init__(self, f, func):
                self.f = f
                self.func = func

            def __call__(self, *args, **kwargs):
                # _log.debug("Calling %s(%s, %s, %s)" %(self.f, self.func, args,  kwargs))
                return self.func(*args, **kwargs)

        if hasattr(self.kserver, name) and callable(getattr(self.kserver, name)):
            return caller(self.call, getattr(self.kserver, name))
        else:
            # Default behaviour
            raise AttributeError

    def get_port(self):
        return self.port

    def stop(self):
        result = threads.blockingCallFromThread(reactor, self.port.stopListening)


def normal_test(match):
    def test(obj):
        if obj != match:
            print("%s != %s" % (repr(obj), repr(match)))
        return obj == match
    return test

def json_test(match):
    try:
        jmatch = json.loads(match)
    except:
        print("Not JSON in json test!!!")
        return False
    def test(obj):
        try:
            jobj = json.loads(obj)
        except:
            print("Not JSON in json test!!!")
            return False
        if jobj != jmatch and not isinstance(jobj, list) and not isinstance(jmatch, list):
            print("%s != %s" % (repr(jobj), repr(jmatch)))
        if isinstance(jobj, list) and isinstance(jmatch, list):
            return set(jobj) == set(jmatch)
        return jobj == jmatch
    return test


def do_sync(func, **kwargs):
    test = None
    timeout = .2
    if 'timeout' in kwargs:
        timeout = kwargs.pop('timeout')
    if 'test' in kwargs:
        test = kwargs.pop('test')

    q = Queue.Queue()

    def respond(value):
        q.put(value)

    d = func(**kwargs)
    d.addCallback(respond)
    try:
        a = q.get(timeout=timeout)
    except Queue.Empty:
        assert False

    if test is not None:
        assert test(a)


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    def fin():
        reactor.callFromThread(reactor.stop)
    request.addfinalizer(fin)
    print "hejsan"

@pytest.mark.slow
class TestKAppend(object):
    test_nodes = 20

    def test_append(self, monkeypatch):

        a = KNet(self.test_nodes)
        a.start()
        try:

            item = ["apa"]
            test_str = json.dumps(item)

            # set(["apa"])
            do_sync(a.get_rand_node().append, key="kalas", value=test_str, test=normal_test(True))
            do_sync(a.get_rand_node().append, key="kalas", value=test_str, test=normal_test(True))
            do_sync(a.get_rand_node().append, key="kalas", value=test_str, test=normal_test(True))
            do_sync(a.get_rand_node().append, key="kalas", value=test_str, test=normal_test(True))

            match_str = json.dumps(item)
            do_sync(a.get_rand_node().get_concat, key="kalas", test=json_test(match_str))

            # set(["apa", "elefant", "tiger"])
            test_str2 = json.dumps(["elefant", "tiger"])
            do_sync(a.get_rand_node().append, key="kalas", value=test_str2, test=normal_test(True))

            match_str = json.dumps(["apa", "elefant", "tiger"])
            do_sync(a.get_rand_node().get_concat, key="kalas", test=json_test(match_str))

            # set(["apa", "tiger"])
            test_str3 = json.dumps(["elefant"])
            do_sync(a.get_rand_node().remove, key="kalas", value=test_str3, test=normal_test(True))

            match_str = json.dumps(["apa", "tiger"])
            do_sync(a.get_rand_node().get_concat, key="kalas", test=json_test(match_str))

            # set(["apa", "elefant", "tiger"])
            test_str2 = json.dumps(["elefant", "tiger"])
            do_sync(a.get_rand_node().append, key="kalas", value=test_str2, test=normal_test(True))

            match_str = json.dumps(["apa", "elefant", "tiger"])
            do_sync(a.get_rand_node().get_concat, key="kalas", test=json_test(match_str))

            # set(["apa", "elefant", "tiger"])
            test_str4 = json.dumps(["lejon"])
            do_sync(a.get_rand_node().remove, key="kalas", value=test_str4, test=normal_test(True))

            match_str = json.dumps(["apa", "elefant", "tiger"])
            do_sync(a.get_rand_node().get_concat, key="kalas", test=json_test(match_str))

            match_str = json.dumps(item)
            do_sync(a.get_rand_node().set, key="kalas", value=test_str, test=normal_test(True))
            do_sync(a.get_rand_node().get, key="kalas", test=json_test(match_str))

            # Should fail
            do_sync(a.get_rand_node().append, key="kalas", value="apa", test=normal_test(False))

            do_sync(a.get_rand_node().set, key="kalas", value="apa", test=normal_test(True))
            do_sync(a.get_rand_node().get, key="kalas", test=normal_test("apa"))

            # Should fail
            do_sync(a.get_rand_node().append, key="kalas", value="apa", test=normal_test(False))
            do_sync(a.get_rand_node().get, key="kalas", test=normal_test("apa"))

        finally:
            import traceback
            traceback.print_exc()
            a.stop()

    def test_set(self, monkeypatch):

        a = KNet(self.test_nodes)
        a.start()
        try:

            do_sync(a.get_rand_node().set, key="kalas", value="apa", test=normal_test(True))
            do_sync(a.get_rand_node().get, key="kalas", test=normal_test("apa"))

            for _ in range(10):
                test_str = '%030x' % random.randrange(16 ** random.randint(1, 2000))
                do_sync(a.get_rand_node().set, key="kalas", value=test_str, test=normal_test(True))
                do_sync(a.get_rand_node().get, key="kalas", test=normal_test(test_str))

        finally:
            a.stop()


    def test_delete(self, monkeypatch):

        a = KNet(self.test_nodes)
        a.start()
        try:

            # Make the nodes know each other
            for _ in range(10):
                key_str = '%030x' % random.randrange(16 ** random.randint(1, 2000))
                test_str = '%030x' % random.randrange(16 ** random.randint(1, 2000))
                do_sync(a.get_rand_node().set, key=key_str, value=test_str, test=normal_test(True))
                do_sync(a.get_rand_node().get, key=key_str, test=normal_test(test_str))


            do_sync(a.get_rand_node().set, key="kalas", value="apa", test=normal_test(True))
            time.sleep(.7)
            do_sync(a.get_rand_node().get, key="kalas", test=normal_test("apa"))

            for _ in range(3):
                test_str = '%030x' % random.randrange(16 ** random.randint(1, 2000))
                do_sync(a.get_rand_node().set, key="kalas", value=test_str, test=normal_test(True))
                do_sync(a.get_rand_node().get, key="kalas", test=normal_test(test_str))
                do_sync(a.get_rand_node().set, key="kalas", value=None, test=normal_test(True))
                do_sync(a.get_rand_node().get, key="kalas", test=normal_test(None))

        finally:
            a.stop()
