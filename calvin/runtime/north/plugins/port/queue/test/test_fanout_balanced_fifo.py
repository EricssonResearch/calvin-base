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
class TestFanoutBalancedFIFO(TestFanoutRoundRobinFIFO):
    
    routing = "balanced"
    queue_type = "dispatch:balanced"
    num_peers = 3
    
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
        port = self.create_port()
        port._set_state(state)
        # check that 1 token has been consumed
        for i in [1,2,3]:
            self.assertTrue(port.tokens_available(1, "reader-%d" % i))
            self.assertFalse(port.tokens_available(2, "reader-%d" % i))
