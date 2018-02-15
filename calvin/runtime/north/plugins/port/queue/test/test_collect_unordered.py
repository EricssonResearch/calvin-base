import pytest
import unittest

from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

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
class TestCollectUnorderedFIFO(unittest.TestCase):
    
    def setUp(self):
        self.inport = create_port()
        
    def setup_writers(self, n):
        writer_list = [ "writer-%d" % i for i in range(1, n+1)]
        for writer in writer_list:
            self.inport.add_writer(writer, {})
        
    def tearDown(self):
        pass
        
    def testInit(self):
        assert self.inport
        
    def testType(self):
        queue_type = self.inport.queue_type
        self.assertEqual(queue_type, "collect:unordered")
    
    def testGetPeers(self):
        self.setup_writers(3)
        self.assertEqual(set(self.inport.get_peers()), 
                         set(["writer-%d" % i for i in [1,2,3]]))
    def testAddWriter(self):
        self.inport.add_writer("writer", {})
        self.assertTrue("writer" in self.inport.writers)
        
    def testRemoveWriter_Normal(self):
        self.setup_writers(1)
        self.inport.remove_writer("writer-1")
        self.assertTrue("writer-1" not in self.inport.writers)
        
    def testRemoveWriter_Failure(self):
        with self.assertRaises(Exception):
            self.inport.remove_writer(self)
        
        with self.assertRaises(Exception):
            self.inport.remove_writer("no such writer")
        
        
    def testAddReader_Normal(self):
        self.inport.add_reader(None, None)
        
    def testAddReader_Illegal(self):
        pass
            
    def testAddReader_Replication(self):
        # Test replication etc
        pass

    def testRemoveReader_Normal(self):
        self.inport.remove_reader(None)
        
    def testWrite_Normal(self):
        self.setup_writers(3)
        for _ in range(3):
            for i in [1,2,3]:
                self.inport.write(i, "writer-%d" % i)
        for i in [1,2,3]:
            fifo = self.inport.fifo["writer-%d" % i]
            self.assertEqual(fifo[:3], [i,i,i])
        
    def testWrite_QueueFull(self):
        self.setup_writers(2)
        with self.assertRaises(QueueFull):
            for i in range(10):
                self.inport.write("fillme", "writer-1")
    
    def testTokensAvailable_Normal(self):
        self.setup_writers(5)
        self.inport.write(Token("data-1"), "writer-1")
        self.assertTrue(self.inport.tokens_available(1, None))
        self.assertFalse(self.inport.tokens_available(2, None))
        self.inport.write(Token("data-1"), "writer-2")
        self.assertTrue(self.inport.tokens_available(2, None))
        self.assertFalse(self.inport.tokens_available(3, None))
        
    
    def testTokensAvailable_Erroneous(self):
        pass
        
    def testSlotsAvailable_Normal(self):
        self.setup_writers(5)
        
        for i in [1,2,3,4,5]:
            self.assertTrue(self.inport.slots_available(self.inport.N-1, "writer-%d" % i))
        
        for i in [1,2,3]:
            self.inport.write(Token("data"), "writer-%d" % i)
        for w in self.inport.writers:
            if w in ["writer-%d" % i for i in [1,2,3]]:
                self.assertTrue(self.inport.slots_available(self.inport.N-2, w))
            else:
                self.assertTrue(self.inport.slots_available(self.inport.N-1, w))

    def testSlotsAvailable_Failure(self):
        pass

    def testPeek_Normal(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        for i in [1,2,3]:
            self.assertEqual(self.inport.peek(None).value, "data-%d" % i)
        for i in [1,2,3]:
            self.assertEqual(self.inport.peek(None).value, "data-%d" % (i+3))
        
    def testPeek_Failure(self):
        self.setup_writers(3)
        with self.assertRaises(QueueEmpty):
            self.inport.peek(None)

    def testCancel(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        data_1 = []
        for i in [1,2,3]:
            data_1 += [self.inport.peek(None).value]
        self.assertEqual(data_1, ["data-%d" % i for i in [1,2,3]])
        self.inport.cancel(None)
        data_2 = []
        try :
            while True:
                data_2 += [self.inport.peek(None).value]
        except QueueEmpty:
            pass
        self.assertEqual(data_2, ["data-%d" % i for i in [1,2,3,4,5,6]])
        
    def testCommit(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        data = []
        for i in [1,2,3,4,5,6]:
            data += [ self.inport.peek(None).value ]
        self.inport.commit(None)
        # should be empty now
        with self.assertRaises(QueueEmpty):
            self.inport.peek(None)
        # ensure the data was as expected
        self.assertEqual(data, ["data-%d" % i for i in [1,2,3,4,5,6]])
                
    def testSerialize(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        for i in [1,2,3]:
            self.inport.peek(None)
        state = self.inport._state()
        port = create_port()
        port._set_state(state)
        for i in [1,2,3]:
            self.assertEqual(port.peek(None).value, "data-%d" % (i+3))
