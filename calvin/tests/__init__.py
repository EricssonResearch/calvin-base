
from mock import Mock

from calvin.runtime.north import metering


class DummyNode:

    def __init__(self):
        self.id = id(self)
        self.pm = Mock()
        self.storage = Mock()
        self.control = Mock()
        self.metering = metering.set_metering(metering.Metering(self))

    def calvinsys(self):
        return None
