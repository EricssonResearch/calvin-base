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

from calvin.requests import calvinresponse
from calvin.utilities import calvinuuid
from calvin.runtime.north import storage
from calvin.runtime.north import appmanager
from calvin.runtime.south.async import threads
from calvin.utilities.calvin_callback import CalvinCB
from calvin.tests import DummyNode
from calvin.tests.helpers_twisted import create_callback, wait_for
from calvin.utilities import calvinconfig
import calvin.tests
import Queue
import pytest
import time

# So it skipps if we dont have twisted plugin
def _dummy_inline(*args):
    pass

if not hasattr(pytest, 'inlineCallbacks'):
    pytest.inlineCallbacks = _dummy_inline

def setup_module(module):
    calvinconfig.get().set('global', 'storage_type', 'dht')

@pytest.mark.skipif(pytest.inlineCallbacks == _dummy_inline,
                    reason="No inline twisted plugin enabled, please use --twisted to py.test")
class TestSetFlushAndGet(object):

    @pytest.inlineCallbacks
    def test_late_start(self):
        self.q = Queue.Queue()
        self.q2 = Queue.Queue()

        def cb(key, value):
            self.q2.put({"key": key, "value": value})

        def started_cb(started):
            self.q.put(started)

        cb, d = create_callback(timeout=2)
        self.storage = storage.Storage(DummyNode())
        self.storage.start('', cb)
        self.storage2 = storage.Storage(DummyNode())
        self.storage.set("test", "1", 1, None)
        self.storage.set("test", "2", 2, None)
        self.storage.set("test", "3", 3, None)

        assert "test1" in self.storage.localstore
        assert "test2" in self.storage.localstore
        assert "test3" in self.storage.localstore

        cb2, d = create_callback(timeout=2)
        self.storage2.start('', cb2)
        value = yield d
        # print value
        assert value[0][0]

        yield wait_for(self.storage.localstore.keys, condition=lambda x: not x())
        assert not self.storage.localstore.keys()

        cb, d = create_callback()
        self.storage.get("test", "3", cb)
        a, kw = yield d
        assert a[0] == "3" and a[1] == 3

        self.storage.stop()
        self.storage2.stop()


@pytest.mark.skipif(pytest.inlineCallbacks == _dummy_inline,
                    reason="No inline twisted plugin enabled, please use --twisted to py.test")
class TestStorageStarted(object):

    @pytest.inlineCallbacks
    def setup_class(self):
        self.storage = storage.Storage(DummyNode())
        self.storage.start()
        yield threads.defer_to_thread(time.sleep, .01)

    @pytest.inlineCallbacks
    def teardown_class(self):
        yield threads.defer_to_thread(self.storage.stop)
        yield threads.defer_to_thread(time.sleep, .01)

    @pytest.inlineCallbacks
    def test_node_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        node = calvin.tests.TestNode(["127.0.0.1:5000"])
        self.storage.add_node(node, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.OK

        self.storage.get_node(node.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["value"] == {u'attributes': {u'indexed_public': [], u'public': {}}, u'control_uris': [u'127.0.0.1:5000'], u'uris': [u'127.0.0.1:5000']}

        self.storage.delete_node(node, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.OK

        self.storage.get_node(node.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.NOT_FOUND

    @pytest.inlineCallbacks
    def test_application_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        application = appmanager.Application(calvinuuid.uuid(
            'APP'), "test_app", [calvinuuid.uuid('ACTOR'), calvinuuid.uuid('ACTOR')], calvinuuid.uuid("NODE"), None)

        self.storage.add_application(application, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.OK

        self.storage.get_application(application.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["value"]["name"] == application.name

        self.storage.delete_application(application.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.OK

        self.storage.get_application(application.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.NOT_FOUND

    @pytest.inlineCallbacks
    def test_actor_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        port1 = calvin.tests.TestPort("out", "out")
        port2 = calvin.tests.TestPort("in", "in", )

        port1.peers = [("local", port2.id)]
        port2.peers = [("local", port1.id)]

        actor = calvin.tests.TestActor("actor1", "type1", {}, {port1.name: port1})

        self.storage.add_actor(actor, calvinuuid.uuid("NODE"), cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.OK

        self.storage.get_actor(actor.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["value"]["name"] == actor.name

        self.storage.delete_actor(actor.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.OK

        self.storage.get_actor(actor.id, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert isinstance(value["value"], calvinresponse.CalvinResponse) and value["value"] == calvinresponse.NOT_FOUND


@pytest.mark.essential
@pytest.mark.skipif(pytest.inlineCallbacks == _dummy_inline,
                    reason="No inline twisted plugin enabled, please use --twisted to py.test")
class TestStorageNotStarted(object):

    @pytest.inlineCallbacks
    def setup_class(self):
        self.storage = storage.Storage(DummyNode())
        yield threads.defer_to_thread(time.sleep, .01)

    @pytest.inlineCallbacks
    def teardown_class(self):
        yield threads.defer_to_thread(time.sleep, .001)

    @pytest.inlineCallbacks
    def test_node_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        node = calvin.tests.TestNode(["127.0.0.1:5000"])
        self.storage.add_node(node)
        self.storage.get_node(node_id=node.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["key"] == node.id and value["value"] == {u'attributes': {u'indexed_public': [], u'public': {}},
                                                              u'control_uris': [u'127.0.0.1:5000'], 'uris': node.uris}

        self.storage.delete_node(node, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value
        assert node.id not in self.storage.localstore

    @pytest.inlineCallbacks
    def test_application_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        application = appmanager.Application(calvinuuid.uuid(
            'APP'), "test_app", [calvinuuid.uuid('ACTOR'), calvinuuid.uuid('ACTOR')], calvinuuid.uuid("NODE"), None)

        self.storage.add_application(application, cb=CalvinCB(cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        # print value

        self.storage.get_application(
            application.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        # print value
        assert value["key"] == application.id and value[
            "value"]["name"] == application.name

        self.storage.delete_application(application.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert application.id not in self.storage.localstore

    @pytest.inlineCallbacks
    def test_actor_and_port_functions(self):
        self.q = Queue.Queue()

        def cb(key, value):
            self.q.put({"key": key, "value": value})

        port1 = calvin.tests.TestPort("out", "out")
        port2 = calvin.tests.TestPort("in", "in", )

        port1.peers = [("local", port2.id)]
        port2.peers = [("local", port1.id)]

        actor1 = calvin.tests.TestActor("actor1", "type1", {}, {port1.name: port1})
        actor2 = calvin.tests.TestActor("actor2", "type2", {port2.name: port2}, {})

        self.storage.add_actor(actor1, calvinuuid.uuid("NODE"))
        value = self.storage.get_actor(actor1.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["key"] == actor1.id and value[
            "value"]["name"] == actor1.name

        assert value["value"]["name"] == actor1.name
        assert value["value"]["type"] == actor1._type
        assert value["value"]["inports"] == []
        assert value["value"]["outports"][0]["id"] == port1.id

        value = self.storage.get_port(port1.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["key"] == port1.id
        assert value["value"]["name"] == port1.name
        assert value["value"]["peers"] == [("local", port2.id)]

        self.storage.add_actor(actor2, calvinuuid.uuid("NODE"))
        value = self.storage.get_actor(actor2.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["key"] == actor2.id
        assert value["value"]["name"] == actor2.name
        assert value["value"]["type"] == actor2._type
        assert value["value"]["inports"][0]["id"] == port2.id
        assert value["value"]["outports"] == []

        value = self.storage.get_port(port2.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value["key"] == port2.id
        assert value["value"]["name"] == port2.name
        assert value["value"]["peers"] == [("local", port1.id)]

        self.storage.delete_actor(actor1.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value
        assert actor1.id not in self.storage.localstore

        self.storage.delete_port(port1.id, cb=CalvinCB(func=cb))
        yield wait_for(self.q.empty, condition=lambda x: not x())
        value = self.q.get(timeout=.001)
        assert value
        assert port1.id not in self.storage.localstore
