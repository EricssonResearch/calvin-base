import pytest

pytest_unittest = pytest.mark.unittest

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueEmpty

from calvin.runtime.north.plugins.port.queue.test.test_fanout_round_robin_fifo import TestFanoutRoundRobinFIFO
class DummyPort(object):
    pass

def find_data(data, port):
    for r in port.readers:
        if data in port.fifo[r]:
            return r
    raise Exception("Data '%s' not found in any reader" % (data, ))
    
@pytest_unittest    
class TestFanoutRandomFIFO(TestFanoutRoundRobinFIFO):

    routing = "random"
    queue_type = "dispatch:random"
    num_peers = 3

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
        port = self.create_port()
        port._set_state(state)
        # check that 1 token has been consumed
        # check that there are 6-consumed tokens total:
        available = 0
        for r, f in self.outport.fifo.items():
            while self.outport.tokens_available(1, r):
                self.outport.peek(r)
                available += 1
        self.assertEqual(4 - consumed, available)
