import pytest
import unittest

from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

pytest_unittest = pytest.mark.unittest

class DummyPort(object):
    pass


def create_port():
    port = DummyPort()
    port.properties = {'routing': "dispatch-ordered", "direction": "out"}
    return queue.get(port)

@pytest_unittest
class TestFanoutOrderedFIFO(unittest.TestCase):
    
    def setUp(self):
        self.outport = create_port()
        
    def setup_readers(self, n):
        reader_list = [ "reader-%d" % i for i in range(1, n+1)]
        for reader in reader_list:
            self.outport.add_reader(reader, {})
        self.outport._reset_turn() # Not the way to do it
        self.outport.set_config({"port-order": reader_list})
        
    def tearDown(self):
        pass
        
    def testInit(self):
        assert self.outport
        
    def testType(self):
        queue_type = self.outport.queue_type
        self.assertEqual(queue_type, "dispatch:ordered")
    
    def testGetPeers(self):
        self.setup_readers(3)
        self.assertEqual(set(self.outport.get_peers()), set(["reader-%d" % i for i in [1,2,3]]))
    
    def testAddWriter(self):
        # Not implemented
        self.outport.add_writer(None, None)
        
    def testRemoveWriter(self):
        # Not implemented
        self.outport.remove_writer(None)
        
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
        self.setup_readers(3)
        for _ in range(3):
            for i in [1,2,3]:
                self.outport.write(i, None)
        for i in [1,2,3]:
            fifo = self.outport.fifo["reader-%d" % i]
            self.assertEqual(fifo[:3], [i,i,i])
        
    def testWrite_QueueFull(self):
        self.setup_readers(2)
        with self.assertRaises(QueueFull):
            for i in range(10):
                self.outport.write("fillme", None)
    
    def testTokensAvailable_Normal(self):
        self.setup_readers(5)
        self.outport.write("data-1", None)
        for r in self.outport.readers:
            if r == "reader-1":
                self.assertTrue(self.outport.tokens_available(1, r))
            else:
                self.assertTrue(self.outport.tokens_available(0, r))
        self.outport.write("data-2", None)
        for r in self.outport.readers:
            if r in ["reader-%d" % i for i in [1,2]]:
                self.assertTrue(self.outport.tokens_available(1, r))
            else:
                self.assertTrue(self.outport.tokens_available(0, r))
        for i in [3,4,5,1,2,3,4,5]:
            self.outport.write("data-%d" % i, None)
        for r in self.outport.readers:
            self.assertTrue(self.outport.tokens_available(2, r))
    
    def testTokensAvailable_Erroneous(self):
        self.setup_readers(2)
        self.outport.write("data", None)
        self.assertFalse(self.outport.tokens_available(1, "reader-2"))
        
        with self.assertRaises(Exception):
            self.outport.tokens_available(1, "no such reader")
        
    def testSlotsAvailable_Normal(self):
        self.setup_readers(5)
        
        self.assertTrue(self.outport.slots_available(self.outport.N-1, None))
        
        for i in range(3):
            self.outport.write("data", None)
        for r in self.outport.readers:
            if r in ["reader-%d" % i for i in [1,2,3]]:
                self.assertTrue(self.outport.slots_available(self.outport.N-2, None))
            else:
                self.assertTrue(self.outport.slots_available(self.outport.N-1, None))

    def testSlotsAvailable_Failure(self):
        pass

    def testPeek_Normal(self):
        self.setup_readers(3)
        for i in [1,2,3,4,5,6]:
            self.outport.write("data-%d" % i, None)
        for i in [1,2,3]:
            self.assertEqual(self.outport.peek("reader-%d" % i), "data-%d" % i)
        for i in [1,2,3]:
            self.assertEqual(self.outport.peek("reader-%d" % i), "data-%d" % (i+3))
        
        
    def testPeek_Failure(self):
        self.setup_readers(3)
        with self.assertRaises(QueueEmpty):
            self.outport.peek("reader-1")

    def testCancel(self):
        self.setup_readers(3)
        for i in [1,2,3,4,5,6]:
            self.outport.write("data-%d" % i, None)
        for i in [1,2,3]:
            self.outport.peek("reader-%d" % i)
        self.outport.cancel("reader-2")
        self.assertEqual(self.outport.peek("reader-2"), "data-2")
        self.assertEqual(self.outport.peek("reader-2"), "data-5")
        
    def testCommit(self):
        self.setup_readers(3)
        for i in [1,2,3,4,5,6]:
            self.outport.write("data-%d" % i, None)
        for i in [1,2,3]:
            self.outport.peek("reader-%d" % i)
        self.outport.commit("reader-2")
        self.outport.cancel("reader-2")
        self.assertEqual(self.outport.peek("reader-2"), "data-5")
        
    def testSetConfig_Failure(self):
        with self.assertRaises(Exception):
            self.outport.set_config({'port-order': ["reader-%d" % i for i in [1,2,3]]})
            
    def testSetConfig_Normal(self):
        reader_list = ["reader-%d" % i for i in [1,2,3,4]]
        for reader in reader_list:
            self.outport.add_reader(reader, {})
        self.outport.set_config(reader_list)
        
    def testSerialize(self):
        self.setup_readers(3)
        for i in [1,2,3,4,5,6]:
            self.outport.write(Token("data-%d" % i), None)
        for i in [1,2,3]:
            self.outport.peek("reader-%d" % i)
        state = self.outport._state()
        port = create_port()
        port._set_state(state)
        for i in [1,2,3]:
            self.assertEqual(port.peek("reader-%d" % i).value, "data-%d" % (i+3))
