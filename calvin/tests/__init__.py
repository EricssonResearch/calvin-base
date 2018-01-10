
from mock import Mock

from calvin.utilities import calvinuuid
from calvin.runtime.north.plugins.port.queue.fanout_fifo import FanoutFIFO
from calvin.utilities import attribute_resolver

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
        self.id = calvinuuid.uuid("")
        self.master = None

    def store(self):
        pass

class DummySys(object):
    """ Dummy Calvin system object """
    def __init__(self, node=None):
        self._node = node
        pass

    def scheduler_wakeup(self):
        pass

    def scheduler_maintenance_wakeup(self, delay=False):
        pass

    def use_requirement(self, actor, modulename):
        pass

    def require(self, modulename):
        pass

    def has_capability(self, requirement):
        """
        Returns True if "requirement" is satisfied in this system,
        otherwise False.
        """
        return False

    def list_capabilities(self):
        """
        Returns list of requirements this system satisfies
        """
        return []

    def get_node(self):
        return self._node

class TestNode:

    def __init__(self, uris, node_name=None, control_uri=None):
        self.id = calvinuuid.uuid("NODE")
        self.node_name = node_name or self.id
        self.uris = uris
        self.control_uri = control_uri or uris[0]
        self.external_control_uri = self.control_uri
        self.pm = Mock()
        self._calvinsys = DummySys(self)
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
        self._replication_data = _DummyRepSet()

class TestPort:

    def __init__(self, name, direction):
        self.id = calvinuuid.uuid("PORT")
        self.name = name
        self.direction = direction
        self.peers = None
        self.properties = {}
        self.queue = FanoutFIFO({'queue_length': 4, 'direction': direction}, {})

    def is_connected(self):
        return True

    def get_peers(self):
        return self.peers
