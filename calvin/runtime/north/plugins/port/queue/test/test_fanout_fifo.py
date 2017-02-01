import unittest

from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

class DummyPort(object):
    pass

class TestFanoutFIFO(unittest.TestCase):
    
    def setUp(self):
        port = DummyPort()
        port.properties = {'routing': "fanout_fifo", "direction": "out"}
        self.outport = queue.get(port)
    
    def tearDown(self):
        pass
        
    def testInit(self):
        assert self.outport
        
    def testType(self):
        queue_type = self.outport.queue_type
        assert queue_type == "fanout_fifo"
        
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
        
