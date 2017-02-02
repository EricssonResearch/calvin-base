import unittest
import pytest

pytest_unittest = pytest.mark.unittest

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

class DummyPort(object):
    pass

def create_port():
    port = DummyPort()
    port.properties = {'routing': "fanout_fifo", "direction": "out"}
    return queue.get(port)

@pytest_unittest    
class TestFanoutFIFO(unittest.TestCase):
    
    def setUp(self):
        self.outport = create_port()
    
    def tearDown(self):
        pass


    def testInit(self):
        assert self.outport
        
    def testType(self):
        queue_type = self.outport.queue_type
        assert queue_type == "fanout_fifo"
    
    def testGetPeers(self):
        for i in [1,2,3]:
            self.outport.add_reader("reader-%d" % i, {})
        self.assertEqual(set(self.outport.get_peers()), set(["reader-%d" % i for i in [1,2,3]]))
    
    def testAddWriter(self):
        self.outport.add_writer("writer", {})
        assert self.outport.writer == "writer"
        
    def testRemoveWriter(self):
        self.outport.remove_writer("writer") # a nop
        
    def testAddReader_Normal(self):
        self.outport.add_reader("reader-1", {})
        self.assertTrue("reader-1" in self.outport.readers)
        self.outport.add_reader("reader-2", {})
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
        self.assertTrue("data-1" in self.outport.fifo)
        self.outport.write("data-2", None)
        self.assertTrue("data-2" in self.outport.fifo)
        self.assertTrue("data-1" in self.outport.fifo)
        
    def testWrite_QueueFull(self):
        self.outport.add_reader("reader", {})
        with self.assertRaises(QueueFull) as context:
            for i in range(self.outport.N):
                    self.outport.write("data", "reader")
            self.assertTrue("Queue is full" in context.exception)
    
    def testTokensAvailable_Normal(self):
        self.outport.add_reader("reader-1", {})
        self.outport.add_reader("reader-2", {})
        self.outport.write("data", None)
        self.assertTrue(self.outport.tokens_available(1, "reader-1"))
        self.outport.write("more data", None)
        self.assertTrue(self.outport.tokens_available(2, "reader-1"))
        self.assertTrue(self.outport.tokens_available(2, "reader-2"))
        self.outport.peek("reader-1")
        self.assertTrue(self.outport.tokens_available(1, "reader-1"))
        self.assertTrue(self.outport.tokens_available(2, "reader-2"))
    
    def testTokensAvailable_Erroneous(self):
        self.outport.write("data", None)
        self.assertFalse(self.outport.tokens_available(1, "reader"))
        
        self.outport.add_reader("reader-1", {})
        with self.assertRaises(Exception):
            self.outport.tokens_available(1, "reader-2")
        
    def testSlotsAvailable_Normal(self):
        length = self.outport.N
        self.outport.write("data", None)
        self.assertTrue(self.outport.slots_available(length - 2, None))
        self.outport.write("data", None)
        self.assertTrue(self.outport.slots_available(length - 3, None))

    def testPeek_Normal(self):
        self.outport.write("data", None)
        self.outport.add_reader("reader-1", {})
        self.outport.add_reader("reader-2", {})
        d = self.outport.peek("reader-1")
        self.assertTrue(d == "data")
        d = self.outport.peek("reader-2")
        self.assertTrue(d == "data")
        
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
        self.outport.add_reader("reader", {})
        self.outport.write("data", None)
        d_1 = self.outport.peek("reader")
        self.outport.cancel("reader")
        d_2 = self.outport.peek("reader")
        self.assertEqual(d_1, d_2)
        
    def testCommit(self):
        self.outport.add_reader("reader-1", {})
        self.outport.add_reader("reader-2", {})
        self.outport.write("data-1", None)
        self.outport.write("data-2", None)
        d_1 = self.outport.peek("reader-1")
        self.outport.commit("reader-1")
        d_2 = self.outport.peek("reader-2")
        self.outport.commit("reader-2")
        self.assertEqual(d_1, d_2)

    def testSerialize(self):
        self.outport.add_reader("reader-1", {})
        self.outport.add_reader("reader-2", {})
        self.outport.add_reader("reader-3", {})
        # write some tokens
        for i in [1,2,3,4]:
                self.outport.write(Token("data-%d" % i), None)
        # peek at the tokens (will consume 1 token)
        for i in [1,2,3]:
            self.outport.peek("reader-%d" % i)
        # save state
        state = self.outport._state()
        # recreate port
        port = create_port()
        port._set_state(state)
        # check that 1 token has been consumed
        for i in [1,2,3]:
            self.assertEqual(port.peek("reader-%d" % i).value, "data-%d" % 2)
    
    def testSerialize_remap(self):
        self.outport.add_reader("reader-1", {})
        self.outport.add_reader("reader-2", {})
        self.outport.add_reader("reader-3", {})
        # write some tokens
        for i in [1,2,3,4]:
                self.outport.write(Token("data-%d" % i), None)
        # peek at the tokens (will consume 1 token)
        for i in [1,2,3]:
            self.outport.peek("reader-%d" % i)
        # save state
        remap = {"reader-%d" % i: "xreader-%d" % i for i in [1,2,3]}
        state = self.outport._state(remap)
        # recreate port
        port = create_port()
        port._set_state(state)
        # check that no tokens available
        for i in [1,2,3]:
            self.assertFalse(port.tokens_available(1, "xreader-%d" % i))
        # check that no old ports remain
        for i in [1,2,3]:
            self.assertFalse("reader-%d" % i in port.readers)
