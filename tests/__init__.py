
from unittest.mock import Mock

from calvin.common import calvinuuid
from calvin.common import attribute_resolver

class SerMock(Mock):
    def _todict(self):
        pass
    def todict(self):
        pass

    def str(self):
        return self.__dict__

class DummyNode:

    def __init__(self):
        self.id = calvinuuid.uuid("NODE")
        self.control_uri = "http://localhost:5001"
        self.pm = Mock()
        self.storage = Mock()
        self.control = Mock()
        self.attributes = attribute_resolver.AttributeResolver({})

    def calvinsys(self):
        return None

class _DummyRepSet:
    def __init__(self):
        self.id = None  # calvinuuid.uuid("")
        self.original_actor_id = None
        self.index = 0

    def store(self):
        pass

class TestNode:

    def __init__(self, uris, node_name=None, control_uri=None):
        self.id = calvinuuid.uuid("NODE")
        self.node_name = node_name or self.id
        self.uris = uris
        self.control_uri = control_uri or uris[0]
        self.external_control_uri = self.control_uri
        self.pm = Mock()
        self.storage = Mock()
        self.control = Mock()
        self.attributes = attribute_resolver.AttributeResolver({})

class TestActor:

    def __init__(self, name, type, inports, outports):
        self.id = calvinuuid.uuid("ACTOR")
        self.name = name
        self._type = type
        self.inports = inports
        self.outports = outports
        self._replication_id = _DummyRepSet()

