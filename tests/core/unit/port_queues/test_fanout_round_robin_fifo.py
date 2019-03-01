import unittest
import pytest

pytest_unittest = pytest.mark.unittest

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

class DummyPort(object):
    pass

def find_data(data, port):
    for r in port.readers:
        if data in port.fifo[r]:
            return r
    raise Exception("Data '%s' not found in any reader" % (data, ))
    
@pytest_unittest    
class TestFanoutRoundRobinFIFO(unittest.TestCase):

    routing = "round-robin"
    queue_type = "dispatch:round-robin"
    num_peers = 3
    
    def create_port(self):
        port = DummyPort()
        port.properties = {'routing': self.routing, "direction": "out",
                            'nbr_peers': self.num_peers}
        return queue.get(port)
        
    def setUp(self):
        self.outport = self.create_port()
        self.setup_readers()
    
    def setup_readers(self):
        for i in range(1, self.outport.nbr_peers+1):
            self.outport.add_reader("reader-%d" % i, {})

    def tearDown(self):
        pass

    def testInit(self):
        assert self.outport
        
    def testType(self):
        self.assertEqual(self.queue_type, self.outport.queue_type)
    
    def testGetPeers(self):
        self.assertEqual(set(self.outport.get_peers()), set(["reader-%d" % i for i in [1,2,3]]))
    
    def testAddWriter(self):
        self.outport.add_writer("writer", {}) # a nop
        
    def testRemoveWriter(self):
        self.outport.remove_writer("writer") # a nop
        
    def testAddReader_Normal(self):
        self.assertTrue("reader-1" in self.outport.readers)
        self.assertTrue("reader-2" in self.outport.readers)
        # Add again
        self.outport.add_reader("reader-2", {})
        self.assertTrue("reader-2" in self.outport.readers)
        
    def testAddReader_Illegal(self):
        with self.assertRaises(Exception) as context:
            self.outport.add_reader(None, {})
            self.assertTrue('Not a string: None' in context.exception)
            
    def testAddReader_Replication(self):
        # Test replication etc
        pass

    def testRemoveReader_Normal(self):
        self.outport.add_reader("reader", {})
        self.outport.remove_reader("reader")
        self.assertTrue("reader" not in self.outport.readers)
        # remove again
        self.outport.remove_reader("reader") # a nop
        
    def testWrite_Normal(self):
        # self.outport.add_reader("reader", {})
        self.outport.write("data-1", None)
        self.assertTrue("data-1" in self.outport.fifo["reader-1"])
        self.outport.write("data-2", None)
        self.assertTrue("data-2" in self.outport.fifo["reader-2"])
        self.assertTrue("data-1" in self.outport.fifo["reader-1"])
        
    def testWrite_QueueFull(self):
        with self.assertRaises(QueueFull) as context:
            for i in range(self.outport.N*self.outport.nbr_peers):
                    self.outport.write("data", "reader")
            self.assertTrue("Queue is full" in context.exception)
    
    def testTokensAvailable_Normal(self):
        self.outport.write("data", None)
        self.assertTrue(self.outport.tokens_available(1, "reader-1"))
        self.outport.write("more data", None)
        self.assertTrue(self.outport.tokens_available(1, "reader-1"))
        self.assertTrue(self.outport.tokens_available(1, "reader-2"))
        self.outport.peek("reader-1")
        self.assertTrue(self.outport.tokens_available(0, "reader-1"))
        self.assertTrue(self.outport.tokens_available(1, "reader-2"))
    
    def testTokensAvailable_Erroneous(self):
        with self.assertRaises(Exception):
            self.outport.tokens_available(1, "no such reader")
        
    def testSlotsAvailable_Normal(self):
        length = self.outport.N
        self.outport.write("data", None)
        self.assertTrue(self.outport.slots_available(length - 2, None))
        self.outport.write("data", None)
        self.assertTrue(self.outport.slots_available(length - 3, None))

    def testPeek_Normal(self):
        self.outport.write("data", None)
        d = self.outport.peek("reader-1")
        self.assertTrue(d == "data")
        with self.assertRaises(QueueEmpty):
            self.outport.peek("reader-2")

        with self.assertRaises(QueueEmpty):
            self.outport.peek("reader-3")
        
    def testPeek_Failure(self):
        # no data
        self.outport.add_reader("reader", {})
        with self.assertRaises(QueueEmpty) as context:
            self.outport.peek("reader")
            print context
        # unknown reader
        self.outport.write("data", None)
        with self.assertRaises(Exception):
            self.outport.peek("unknown reader")

    def testCancel(self):
        self.outport.write("data", None)
        d_1 = self.outport.peek("reader-1")
        self.outport.cancel("reader-1")
        d_2 = self.outport.peek("reader-1")
        self.assertEqual(d_1, d_2)
        
    def testCommit(self):
        self.outport.write("data-1", None)
        self.outport.write("data-2", None)
        d_1 = self.outport.peek("reader-1")
        self.assertEqual(d_1, "data-1")
        self.outport.commit("reader-1")
        d_2 = self.outport.peek("reader-2")
        self.outport.commit("reader-2")
        self.assertEqual(d_2, "data-2")


    def testSerialize(self):
        # write some tokens
        for i in [1,2,3,4,5,6]:
                self.outport.write(Token("data-%d" % i), None)
        # peek at the tokens (will consume 1 token)
        for i in [1,2,3]:
            self.outport.peek("reader-%d" % i)
        # save state
        state = self.outport._state()
        # recreate port
        port = self.create_port()
        port._set_state(state)
        # check that 1 token has been consumed
        for i in [1,2,3]:
            self.assertEqual(port.peek("reader-%d" % i).value, "data-%d" % (i+3))
