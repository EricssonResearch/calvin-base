import pytest

from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueEmpty
from calvin.runtime.north.plugins.port.queue.test.test_collect_unordered import TestCollectUnorderedFIFO
pytest_unittest = pytest.mark.unittest

class DummyPort(object):
    pass


def create_port(routing="collect-unordered"):
    port = DummyPort()
    port.properties = {'routing': routing, "direction": "in"}
    return queue.get(port)

def unwrap(data):
    return data.value.items()[0]
            
@pytest_unittest
class TestCollectUnorderedFIFOTagged(TestCollectUnorderedFIFO):
    
    def setUp(self):
        self.inport = create_port(routing="collect-tagged")
        
    def testType(self):
        queue_type = self.inport.queue_type
        self.assertEqual(queue_type, "collect:tagged")

    def testSerialize(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        for i in [1,2,3]:
            self.inport.peek(None)
        state = self.inport._state()
        port = create_port(routing="collect-tagged")
        port._set_state(state)
        for i in [1,2,3]:
            tag, data = unwrap(port.peek(None))
            self.assertEqual(tag, "writer-%d" % i)
            self.assertEqual(data, "data-%d" % (i+3))

    def testPeek_Normal(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        for i in [1,2,3]:
            tag, data = unwrap(self.inport.peek(None))
            self.assertEqual(tag, "writer-%d" % i)
            self.assertEqual(data, "data-%d" % i)
        for i in [1,2,3]:
            tag, data = unwrap(self.inport.peek(None))
            self.assertEqual(tag, "writer-%d" % i)
            self.assertEqual(data, "data-%d" % (i+3))

    def testCancel(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        data_1 = {}
        for i in [1,2,3]:
            tag, data = unwrap(self.inport.peek(None))
            data_1.setdefault(tag, []).append(data)
        
        self.inport.cancel(None)
        data_2 = {}
        try :
            while True:
                tag, data = unwrap(self.inport.peek(None))
                data_2.setdefault(tag, []).append(data)
        except QueueEmpty:
            pass
        for tag, data in data_1.items():
            self.assertEqual(data, data_2[tag][:len(data)])
        
    def testCommit(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        values = {}
        for i in [1,2,3,4,5,6]:
            tag, data = unwrap(self.inport.peek(None))
            values.setdefault(tag, []).append(data)
        self.inport.commit(None)
        # should be empty now
        with self.assertRaises(QueueEmpty):
            self.inport.peek(None)
        for tag, data in values.items():
            for i in [1,2,3]:
                if tag == "writer-%d" % i:
                    self.assertEqual(["data-%d" % d for d in [i, i+3]], data)
