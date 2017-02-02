import unittest
import pytest

pytest_unittest = pytest.mark.unittest

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty

class DummyPort(object):
    pass

def create_port(num_peers, routing):
    port = DummyPort()
    port.properties = {'routing': routing, "direction": "out",
                        'nbr_peers': num_peers}
    return queue.get(port)

def find_data(data, port):
    for r in port.readers:
        if data in port.fifo[r]:
            return r
    raise Exception("Data '%s' not found in any reader" % (data, ))
    
@pytest_unittest    
class TestScheduledFIFO(unittest.TestCase):

    routing = "round-robin"
    queue_type = "scheduled_fifo:round-robin"
    peers = 3
    
    def setUp(self):
        self.outport = create_port(routing=self.routing, num_peers=self.peers)
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
        port = create_port(routing=self.routing, num_peers=self.outport.nbr_peers)
        port._set_state(state)
        # check that 1 token has been consumed
        for i in [1,2,3]:
            self.assertEqual(port.peek("reader-%d" % i).value, "data-%d" % (i+3))
    
    def testSerialize_remap(self):
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
        port = create_port(routing=self.routing, num_peers=self.outport.nbr_peers)
        port._set_state(state)
        # check that no tokens available
        for i in [1,2,3]:
            self.assertTrue(port.tokens_available(0, "xreader-%d" % i))
        # check that no old ports remain
        for i in [1,2,3]:
            self.assertFalse("reader-%d" % i in port.readers)

@pytest_unittest    
class TestScheduledFIFORandom(TestScheduledFIFO):

    routing = "random"
    queue_type = "scheduled_fifo:random"
    peers = 3

    def testWrite_Normal(self):
        # self.outport.add_reader("reader", {})
        self.outport.write("data-1", None)
        found_in = find_data("data-1", self.outport)
        self.assertTrue(found_in is not None)
        self.outport.write("data-2", None)
        self.assertTrue("data-1" in self.outport.fifo[found_in])
        found_in = find_data("data-2", self.outport)
        self.assertTrue(found_in is not None)
    
    def testTokensAvailable_Normal(self):
        self.outport.write("data", None)
        reader1, reader2, reader3 = (None, None, None)
        reader1 = find_data("data", self.outport)
        self.assertTrue(reader1 is not None)
        
        self.outport.write("more data", None)
        reader2 = find_data("more data", self.outport)
        self.assertTrue(reader2 is not None)
        
        d = self.outport.peek(reader1)
        self.assertEqual(d, "data")
        
        self.assertTrue(self.outport.tokens_available(1, reader2))
        
        if reader1 != reader2:
            self.assertTrue(self.outport.tokens_available(0, reader1))

    def testPeek_Normal(self):
        self.outport.write("data", None)
        reader1 = find_data("data", self.outport)
        d = self.outport.peek(reader1)
        self.assertEqual(d, "data")
        for reader in self.outport.readers:
            with self.assertRaises(QueueEmpty):
                self.outport.peek(reader)

    def testCancel(self):
        self.outport.write("data", None)
        reader1 = find_data("data", self.outport)
        d1 = self.outport.peek(reader1)
        self.outport.cancel(reader1)
        d2 = self.outport.peek(reader1)
        self.assertEqual(d1, d2)
        
    def testCommit(self):
        self.outport.write("data-1", None)
        reader1 = find_data("data-1", self.outport)
        d_1 = self.outport.peek(reader1)
        self.outport.commit(reader1)
        self.outport.cancel(reader1)
        with self.assertRaises(QueueEmpty):
            self.outport.peek(reader1)
        self.assertEqual(d_1, "data-1")

    def testSerialize(self):
        # write some tokens
        for i in [1,2,3,4]:
                self.outport.write(Token("data-%d" % i), None)
        # peek at the tokens (will consume 1 token)
        consumed = 0
        for r in self.outport.readers:
            if self.outport.tokens_available(1, r):
                self.outport.peek(r)
                consumed += 1

        # save state
        state = self.outport._state()
        # recreate port
        port = create_port(routing=self.routing, num_peers=self.outport.nbr_peers)
        port._set_state(state)
        # check that 1 token has been consumed
        # check that there are 6-consumed tokens total:
        available = 0
        for r, f in self.outport.fifo.items():
            while self.outport.tokens_available(1, r):
                self.outport.peek(r)
                available += 1
        self.assertEqual(4 - consumed, available)
        
    def testSerialize_remap(self):
        # write some tokens
        for i in [1,2,3,4]:
                self.outport.write(Token("data-%d" % i), None)
        # save state
        remap = {"reader-%d" % i: "xreader-%d" % i for i in [1,2,3]}
        state = self.outport._state(remap)
        # recreate port
        port = create_port(routing=self.routing, num_peers=self.outport.nbr_peers)
        port._set_state(state)
        # check that no tokens available
        for i in [1,2,3]:
            self.assertFalse(port.tokens_available(1, "xreader-%d" % i))
        # check that no old ports remain
        for i in [1,2,3]:
            self.assertFalse("reader-%d" % i in port.readers)

class TestBalancedFIFO(TestScheduledFIFO):
    
    routing = "balanced"
    queue_type = "scheduled_fifo:balanced"
    peers = 3
    
    def testWrite_Normal(self):
        for i in [1,2,3]:
            [ self.outport.write("data-%d" % (i+j), None) for j in [0,3,6] ]
        # 3 tokens in each
        all_data = []
        for i in [1,2,3]:
            data = []
            for j in range(3):
                data += [self.outport.peek("reader-%d" % i)]
            self.assertEquals(len(data), 3)
            all_data += data
        self.assertEquals(set(all_data), set(["data-%d" % i for i in range(1, 10)]))
        for i in [1,2,3]:
            self.assertFalse(self.outport.tokens_available(1, "reader-%d" % i))

    def testSlotsAvailable_Normal(self):
        for i in range(10):
            self.outport.write("data-%d" % i, None)
        self.assertTrue(self.outport.slots_available(2, None))
        self.assertFalse(self.outport.slots_available(3, None))
        self.outport.peek("reader-%d" % 1)
        self.outport.commit("reader-%d" % 1)
        self.assertTrue(self.outport.slots_available(3, None))

    def testTokensAvailable_Normal(self):
        for i in range(1,7):
            self.outport.write("data-%d" % i, None)
        # 2 tokens in each fifo
        for i in [1,2,3]:
            self.assertTrue(self.outport.tokens_available(2, "reader-%d" % i))
        for i in range(1,4):
            self.outport.write("data-%d" % i, None)
        # 3 tokens in each fifo
        for i in [1,2,3]:
            self.assertTrue(self.outport.tokens_available(3, "reader-%d" % i))
        self.outport.peek("reader-1")
        self.outport.peek("reader-3")
        self.outport.commit("reader-1")
        self.outport.commit("reader-3")
        self.assertFalse(self.outport.tokens_available(3, "reader-%d" % 1))
        self.assertFalse(self.outport.tokens_available(3, "reader-%d" % 3))
        self.assertTrue(self.outport.tokens_available(3, "reader-%d" % 2))

    def testPeek_Normal(self):
        for i in [1,2,3]:
            self.outport.write("data-%d" % i, None)
        data = []
        for i in [1,2,3]:
            data += [self.outport.peek("reader-%d" % i)]
        self.assertEqual(set(data), set(["data-%d" % i for i in [1,2,3]]))
        for i in [1,2,3]:
            with self.assertRaises(QueueEmpty):
                self.outport.peek("reader-%d" % i)

    def testCancel(self):
        for i in [1,2,3]:
            self.outport.write("data-%d" % i, None)
        d1 = self.outport.peek("reader-1")
        self.outport.cancel("reader-1")
        d2 = self.outport.peek("reader-1")
        self.assertEqual(d1, d2)
        
    def testCommit(self):
        for i in [1,2,3,4,5,6]:
            self.outport.write("data-%d" % i, None)
        d1 = self.outport.peek("reader-1")
        self.outport.commit("reader-1")
        d2 = self.outport.peek("reader-1")
        self.assertFalse(d1 == d2)

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
        port = create_port(routing=self.routing, num_peers=self.outport.nbr_peers)
        port._set_state(state)
        # check that 1 token has been consumed
        for i in [1,2,3]:
            self.assertTrue(port.tokens_available(1, "reader-%d" % i))
            self.assertFalse(port.tokens_available(2, "reader-%d" % i))
