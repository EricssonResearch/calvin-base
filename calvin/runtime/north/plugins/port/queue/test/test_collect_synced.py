import pytest
import unittest

from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.calvin_token import Token, ExceptionToken
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

pytest_unittest = pytest.mark.unittest

class DummyPort(object):
    pass


def create_port(routing):
    port = DummyPort()
    port.properties = {'routing': routing, "direction": "in"}
    return queue.get(port)

def unwrap(data):
    return data.value.items()[0]
    
@pytest_unittest
class TestCollectSyncedFIFO(unittest.TestCase):
    
    def setUp(self):
        self.inport = create_port(routing="collect-all-tagged")
        
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
        self.assertEqual(queue_type, "collect:all-tagged")
    
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
        for i in [1,2,3,4,5]:
            self.inport.write(Token("data-%d" % i), "writer-%d" % i)
        self.assertTrue(self.inport.tokens_available(1, None))
        for i in [1,2,3]:
            self.inport.write(Token("data-%d" % i), "writer-%d" % i)
        self.assertFalse(self.inport.tokens_available(2, None))
        for i in [4,5]:
            self.inport.write(Token("data-%d" % i), "writer-%d" % i)
        self.assertTrue(self.inport.tokens_available(2, None))

        
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
        
    def testPeek_Failure(self):
        self.setup_writers(3)
        with self.assertRaises(QueueEmpty):
            self.inport.peek(None)

    def testSerialize(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        self.inport.peek(None)
        state = self.inport._state()
        port = create_port(routing="collect-all-tagged")
        port._set_state(state)
        data = self.inport.peek(None).value
        self.assertEqual(data, {"writer-%d" % i: "data-%d" % (i+3) for i in [1,2,3]})

    def testPeek_Normal(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        data = self.inport.peek(None).value
        self.assertEqual(data, {"writer-%d" % i: "data-%d" % i for i in [1,2,3]})
        data = self.inport.peek(None).value
        self.assertEqual(data, {"writer-%d" % i: "data-%d" % (i+3) for i in [1,2,3]})

    def testPeek_Exception(self):
        self.setup_writers(3)
        
        for i in [1,2,3]:
            self.inport.write(Token("data-%d" % i), "writer-%d" % i)
        self.inport.write(Token("data-%d" % (1+3)), "writer-%d" % 1)
        self.inport.write(ExceptionToken(), "writer-%d" % 2)
        self.inport.write(Token("data-%d" % (3+3)), "writer-%d" % 3)
        for i in [1,2,3]:
            self.inport.write(Token("data-%d" % (i+6)), "writer-%d" % i)
        """
            w1: 1 4 7
            w2: 2 e 8
            w3: 3 6 9
        """
        data_1 = self.inport.peek(None).value
        self.assertEqual(data_1, {"writer-%d" % i: "data-%d" % i for i in [1,2,3]})
        """
            w1: 4 7
            w2: e 8
            w3: 6 9
        """
        data_2 = self.inport.peek(None).value
        self.assertEqual(data_2, {"writer-2": 'Exception'})
        """
            w1: 4 7
            w2: 8
            w3: 6 9
        """
        data_3 = self.inport.peek(None).value
        result = {"writer-%d" % i: "data-%d" % (i+3) for i in [1,2,3]}
        result["writer-2"] = "data-8"
        self.assertEqual(data_3, result)
        
        
    def testCancel(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        data_1 = self.inport.peek(None).value
        self.inport.cancel(None)
        data_2 = self.inport.peek(None).value
        self.assertEqual(data_1, data_2)
        data_2 = self.inport.peek(None).value
        self.assertEqual(data_2, {"writer-%d" % i: "data-%d" % (i+3) for i in [1,2,3]})

    def testCommit(self):
        self.setup_writers(3)
        for i in [1,2,3]:
            for j in [0,3]:
                self.inport.write(Token("data-%d" % (i+j)), "writer-%d" % i)
        self.inport.peek(None)
        self.inport.commit(None)
        data_2 = self.inport.peek(None).value
        self.assertEqual(data_2, {"writer-%d" % i: "data-%d" % (i+3) for i in [1,2,3]})
        with self.assertRaises(QueueEmpty):
            self.inport.peek(None)
