import os
import unittest

from calvin.runtime.north.calvin_node import Node
from calvin.runtime.north.appmanager import Application
from calvin.runtime.north.actormanager import ActorManager


class TestStorage(unittest.TestCase):

    def setUp(self):
        ip_addr = None
        try:
            ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
        except:
            import socket
            ip_addr = socket.gethostbyname(socket.gethostname())

        self.uri = "calvinip://%s:%s" % (ip_addr, 5000)
        self.control_uri = "http://%s:%s" % (ip_addr, 5001)
        self.node = Node(self.uri, self.control_uri)
        self.storage = self.node.storage
        self.storage.start()

    def test_set_get(self):
        self.storage.set("test-prefix-", "test-key", "my_value")
        assert self.storage.get("test-prefix-", "test-key") == "my_value"

    def test_get_iter(self):
        self.storage.set("test-iter-prefix-", "test-iter-key", "my_value")
        assert self.storage.get_iter("test-iter-prefix-", "test-iter-key", []) == "my_value"

    def test_append(self):
        self.storage.append("test-append-prefix-", "test-append-key", ["my_value"])
        assert self.storage.get_concat("test-append-prefix-", "test-append-key") == ["my_value"]

    def test_remove(self):
        self.storage.append("test-remove-prefix-", "test-remove-key", ["my_value"])
        assert self.storage.get_concat("test-remove-prefix-", "test-remove-key") == ["my_value"]
        self.storage.remove("test-remove-prefix-", "test-remove-key", ["my_value"])
        assert self.storage.get_concat("test-remove-prefix-", "test-remove-key") == []

    def test_delete(self):
        self.storage.set("test-delete-prefix-", "test-delete-key", "my_value")
        assert self.storage.get("test-delete-prefix-", "test-delete-key") == "my_value"
        self.storage.delete("test-delete-prefix-", "test-delete-key")
        assert self.storage.get("test-delete-prefix-", "test-delete-key") == None

    def test_store_node(self):
        self.storage.add_node(self.node)
        value = self.storage.get_node(self.node.id)
        assert value['uri'] == self.uri
        assert value['control_uri'] == self.control_uri

        self.storage.delete_node(self.node)
        assert self.storage.get_node(self.node.id) == None

    def test_application(self):
        actor_manager = ActorManager(self.node)
        actors = {
            'actor-123': 'actor:src',
            'actor-456': 'actor:snk'
        }
        application = Application("123", "my_app", self.node.id, actor_manager, actors=actors)
        self.storage.add_application(application)

        value = self.storage.get_application(application.id)
        assert value == {
            'actors': ['actor-456', 'actor-123'],
            'ns': 'my_app',
            'actors_name_map': {'actor-456': 'actor:snk', 'actor-123': 'actor:src'},
            'name': 'my_app',
            'origin_node_id': self.node.id
        }

        self.storage.delete_application(application.id)
        assert self.storage.get_application(application.id) == None

    def test_actor(self):
        actor_manager = ActorManager(self.node)
        actor_id = actor_manager.new('std.Identity', {'name': 'identity'})
        actor = actor_manager.actors[actor_id]

        self.storage.add_actor(actor, self.node.id)
        value = self.storage.get_actor(actor.id)
        assert value == {
            'inports': [{'id': actor.inports['token'].id, 'name': 'token'}],
            'outports': [{u'id': actor.outports['token'].id, 'name': 'token'}],
            'is_shadow': False,
            'name': 'identity',
            'node_id': self.node.id,
            'type': 'std.Identity'
        }

        self.storage.delete_actor(actor.id)
        assert self.storage.get_actor(actor.id) == None

    def test_port(self):
        actor_manager = ActorManager(self.node)
        actor_id = actor_manager.new('std.Identity', {'name': 'identity'})
        actor = actor_manager.actors[actor_id]
        port = actor.inports['token']

        self.storage.add_port(port, self.node.id)
        value = self.storage.get_port(port.id)
        assert value == {
            'actor_id': actor.id,
            'connected': False,
            'direction': 'in',
            'name': 'token',
            'node_id': self.node.id,
            'peer': None
        }

        self.storage.delete_port(port.id)
        assert self.storage.get_port(port.id) == None
