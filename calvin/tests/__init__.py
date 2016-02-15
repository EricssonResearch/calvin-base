
from mock import Mock

from calvin.runtime.north import metering
from calvin.utilities import calvinuuid
from calvin.runtime.north.fifo import FIFO


class DummyNode:

    def __init__(self):
        self.id = id(self)
        self.pm = Mock()
        self.storage = Mock()
        self.control = Mock()
        self.metering = metering.set_metering(metering.Metering(self))

    def calvinsys(self):
        return None


class TestNode:

    def __init__(self, uri):
        self.id = calvinuuid.uuid("NODE")
        self.uri = uri


class TestActor:

    def __init__(self, name, type, inports, outports):
        self.id = calvinuuid.uuid("ACTOR")
        self.name = name
        self._type = type
        self.inports = inports
        self.outports = outports


class TestPort:

    def __init__(self, name, direction):
        self.id = calvinuuid.uuid("PORT")
        self.name = name
        self.direction = direction
        self.peer = None
        self.peers = None
        self.fifo = FIFO(5)

    def is_connected(self):
        return True

    def get_peer(self):
        return self.peer

    def get_peers(self):
        return self.peers
