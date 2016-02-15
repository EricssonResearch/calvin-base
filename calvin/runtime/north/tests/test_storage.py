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

from calvin.utilities import calvinuuid
from calvin.runtime.north import storage
from calvin.runtime.north import appmanager
from calvin.runtime.south.plugins.async import threads
from calvin.utilities.calvin_callback import CalvinCB
from calvin.tests import TestNode, TestActor, TestPort
import Queue
import pytest
import time

try:
    import pytest.inlineCallbacks
except ImportError:
    pytest.inlineCallbacks = lambda *args: False


@pytest.mark.interactive
class TestSetFlushAndGet(object):

    @pytest.mark.slow
    @pytest.inlineCallbacks
    def test_late_start(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        def started_cb(started):
            self.q.put(started)

        self.storage = storage.Storage()
        self.storage.set("test", "1", 1, None)
        self.storage.set("test", "2", 2, None)
        self.storage.set("test", "3", 3, None)

        assert "test1" in self.storage.localstore
        assert "test2" in self.storage.localstore
        assert "test3" in self.storage.localstore

        yield threads.defer_to_thread(self.storage.start, CalvinCB(started_cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value

        assert "test1" not in self.storage.localstore
        assert "test2" not in self.storage.localstore
        assert "test3" not in self.storage.localstore

        yield threads.defer_to_thread(self.storage.get, "test", "3", CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value["value"] == 3

        yield threads.defer_to_thread(self.storage.stop)


@pytest.mark.interactive
@pytest.mark.slow
class TestStorageStarted(object):

    @pytest.inlineCallbacks
    def setup_class(self):
        self.storage = storage.Storage()
        yield threads.defer_to_thread(self.storage.start)
        yield threads.defer_to_thread(time.sleep, 2)

    @pytest.inlineCallbacks
    def teardown_class(self):
        yield threads.defer_to_thread(self.storage.stop)
        yield threads.defer_to_thread(time.sleep, 2)

    @pytest.inlineCallbacks
    def test_node_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        yield threads.defer_to_thread(time.sleep, 2)

        node = TestNode("127.0.0.1:5000")
        yield threads.defer_to_thread(self.storage.add_node, node, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is True

        yield threads.defer_to_thread(self.storage.get_node, node.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] == {'uri': node.uri}

        yield threads.defer_to_thread(self.storage.delete_node, node, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is True

        yield threads.defer_to_thread(self.storage.get_node, node.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is None

    @pytest.inlineCallbacks
    def test_application_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        yield threads.defer_to_thread(time.sleep, 2)

        application = appmanager.Application(calvinuuid.uuid(
            'APP'), "test_app", [calvinuuid.uuid('ACTOR'), calvinuuid.uuid('ACTOR')])

        yield threads.defer_to_thread(self.storage.add_application, application, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is True

        yield threads.defer_to_thread(self.storage.get_application, application.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"]["name"] == application.name

        yield threads.defer_to_thread(self.storage.delete_application, application.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is True

        yield threads.defer_to_thread(self.storage.get_application, application.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is None

    @pytest.inlineCallbacks
    def test_actor_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        yield threads.defer_to_thread(time.sleep, 2)

        port1 = TestPort("out", "out")
        port2 = TestPort("in", "in", )

        port1.peers = [("local", port2.id)]
        port2.peer = ("local", port1.id)

        actor = TestActor("actor1", "type1", {}, {port1.name: port1})

        yield threads.defer_to_thread(self.storage.add_actor, actor, calvinuuid.uuid("NODE"), cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is True

        yield threads.defer_to_thread(self.storage.get_actor, actor.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"]["name"] == actor.name

        yield threads.defer_to_thread(self.storage.delete_actor, actor.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is True

        yield threads.defer_to_thread(self.storage.get_actor, actor.id, cb=CalvinCB(cb))
        yield threads.defer_to_thread(time.sleep, 2)
        value = self.q.get(timeout=0.2)
        assert value["value"] is None

@pytest.mark.interactive
class TestStorageNotStarted(object):

    def setup_class(self):
        self.storage = storage.Storage()

    def teardown_class(self):
        pass

    def test_node_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        node = TestNode("127.0.0.1:5000")
        self.storage.add_node(node)
        value = self.storage.get_node(node_id=node.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value["key"] == node.id and value["value"] == {'uri': node.uri}

        self.storage.delete_node(node, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value
        assert node.id not in self.storage.localstore

    def test_application_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        application = appmanager.Application(calvinuuid.uuid(
            'APP'), "test_app", [calvinuuid.uuid('ACTOR'), calvinuuid.uuid('ACTOR')])

        self.storage.add_application(application)
        value = self.storage.get_application(
            application.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value["key"] == application.id and value[
            "value"]["name"] == application.name

        self.storage.delete_application(application.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value
        assert application.id not in self.storage.localstore

    def test_actor_and_port_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        port1 = TestPort("out", "out")
        port2 = TestPort("in", "in", )

        port1.peers = [("local", port2.id)]
        port2.peer = ("local", port1.id)

        actor1 = TestActor("actor1", "type1", {}, {port1.name: port1})
        actor2 = TestActor("actor2", "type2", {port2.name: port2}, {})

        self.storage.add_actor(actor1, calvinuuid.uuid("NODE"))
        value = self.storage.get_actor(actor1.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value["key"] == actor1.id and value[
            "value"]["name"] == actor1.name

        assert value["value"]["name"] == actor1.name
        assert value["value"]["type"] == actor1._type
        assert value["value"]["inports"] == []
        assert value["value"]["outports"][0]["id"] == port1.id

        value = self.storage.get_port(port1.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value["key"] == port1.id
        assert value["value"]["name"] == port1.name
        assert value["value"]["direction"] == port1.direction
        assert value["value"]["peers"] == [["local", port2.id]]

        self.storage.add_actor(actor2, calvinuuid.uuid("NODE"))
        value = self.storage.get_actor(actor2.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value["key"] == actor2.id
        assert value["value"]["name"] == actor2.name
        assert value["value"]["type"] == actor2._type
        assert value["value"]["inports"][0]["id"] == port2.id
        assert value["value"]["outports"] == []

        value = self.storage.get_port(port2.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value["key"] == port2.id
        assert value["value"]["name"] == port2.name
        assert value["value"]["direction"] == port2.direction
        assert value["value"]["peer"] == ["local", port1.id]

        self.storage.delete_actor(actor1.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value
        assert actor1.id not in self.storage.localstore

        self.storage.delete_port(port1.id, cb=CalvinCB(func=cb))
        value = self.q.get(timeout=0.2)
        assert value
        assert port1.id not in self.storage.localstore
