# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import unittest
from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.calvin_token import Token

pytestmark = pytest.mark.unittest


class QueueTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def verify_data(self, write_data, fifo_data):
        print write_data, fifo_data
        for a, b in zip(write_data, fifo_data):
            d = b.value
            self.assertEquals(a, d)

    def test1(self):
        """Adding reader again (reconnect)"""
        f = queue.fanout_fifo.FanoutFIFO(5)
        f.add_reader('p1.id')
        data = ['1', '2', '3', '4']
        for token in data:
            self.assertTrue(f.slots_available(1))
            self.assertTrue(f.write(Token(token)))

        self.verify_data(['1', '2'], [f.peek('p1.id') for _ in range(2)])

        f.commit('p1.id')
        f.add_reader('p1.id')

        self.verify_data(['3', '4'], [f.peek('p1.id') for _ in range(2)])

        self.assertRaises(queue.common.QueueEmpty, f.peek, 'p1.id')

        f.commit('p1.id')

        for token in ['5', '6', '7', '8']:
            self.assertTrue(f.slots_available(1))
            self.assertTrue(f.write(Token(token)))

        self.assertFalse(f.slots_available(1))

        self.verify_data(['5', '6', '7', '8'], [f.peek('p1.id')
                                                for _ in range(4)])
        f.commit('p1.id')

    def test2(self):
        """Multiple readers"""

        f = queue.fanout_fifo.FanoutFIFO(5)
        f.add_reader("r1")
        f.add_reader("r2")

        # Ensure fifo is empty
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertTrue(f.tokens_available(0, "r1"))
        self.assertTrue(f.tokens_available(0, "r2"))

        # Add something
        self.assertTrue(f.write(Token('1')))
        self.assertTrue(f.tokens_available(1, "r1"))
        self.assertTrue(f.tokens_available(1, "r2"))

        # Reader r1 read something
        self.assertTrue(f.peek('r1'))
        f.commit('r1')

        self.assertEquals([True] * 3, [f.write(Token(t)) for t in ['2', '3', '4']])
        self.assertRaises(queue.common.QueueFull, f.write, Token('5'))
        self.verify_data(['2', '3', '4'], [f.peek('r1') for _ in range(3)])
        f.commit("r1")

        # Reader r1 all done, ensure reader r2 can still read
        self.assertTrue(f.tokens_available(4, "r2"))
        self.assertFalse(f.slots_available(1))
        self.assertFalse(f.tokens_available(1, "r1"))

        # Reader r2 reads something
        self.verify_data(['1', '2', '3'], [f.peek("r2") for _ in range(3)])
        f.commit("r2")
        self.assertTrue(f.tokens_available(1, "r2"))

        self.assertTrue(f.write(Token('5')))
        self.verify_data(['4', '5'], [f.peek("r2") for _ in range(2)])

        self.assertFalse(f.tokens_available(1, "r2"))
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r2")
        self.assertTrue(f.tokens_available(1, "r1"))
        self.verify_data(['5'], [f.peek("r1")])

        f.commit("r2")
        f.commit("r1")

        self.assertTrue(f.write(Token('6')))
        self.assertTrue(f.write(Token('7')))
        self.assertTrue(f.write(Token('8')))

        self.assertTrue([f.peek("r1")
                         for _ in range(3)], [f.peek("r2") for _ in range(3)])
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r2")

    def test3(self):
        """Testing commit reads"""
        f = queue.fanout_fifo.FanoutFIFO(5)
        f.add_reader("r1")

        for token in ['1', '2', '3', '4']:
            self.assertTrue(f.slots_available(1))
            self.assertTrue(f.write(Token(token)))

        # Fails, fifo full
        self.assertFalse(f.slots_available(1))
        self.assertRaises(queue.common.QueueFull, f.write, Token('5'))

        # Tentative, fifo still full
        self.verify_data(['1'], [f.peek("r1")])
        self.assertFalse(f.slots_available(1))
        self.assertRaises(queue.common.QueueFull, f.write, Token('5'))

        # commit previous reads, fifo 1 pos free
        f.commit('r1')
        self.assertTrue(f.slots_available(1))
        self.assertTrue(f.write(Token('5')))
        # fifo full again
        self.assertFalse(f.slots_available(1))
        self.assertRaises(queue.common.QueueFull, f.write, Token('5'))

    def test4(self):
        """Testing rollback reads"""
        f = queue.fanout_fifo.FanoutFIFO(5)
        f.add_reader('r1')

        for token in ['1', '2', '3', '4']:
            self.assertTrue(f.slots_available(1))
            self.assertTrue(f.write(Token(token)))

        # fifo full
        self.assertFalse(f.slots_available(1))
        self.assertRaises(queue.common.QueueFull, f.write, Token('5'))

        # tentative reads
        self.verify_data(['1', '2', '3', '4'], [f.peek("r1")
                                                for _ in range(4)])
        # check still tentative
        self.assertTrue(f.tokens_available(0, "r1"))
        self.assertTrue(f.slots_available(0))

        f.cancel("r1")
        self.assertFalse(f.slots_available(1))
        self.assertRaises(queue.common.QueueFull, f.write, Token('5'))
        self.assertTrue(f.tokens_available(4, "r1"))

        # re-read
        self.verify_data(['1'], [f.peek("r1")])
        f.commit("r1")
        self.assertTrue(f.tokens_available(3, "r1"))

        # one pos free in fifo
        self.assertTrue(f.slots_available(1))
        self.assertTrue(f.write(Token('a')))
        self.assertFalse(f.slots_available(1))
        self.assertRaises(queue.common.QueueFull, f.write, Token('b'))

    def test_scheduled_queue_1(self):
        """Round-Robin scheduled queue test"""

        f = queue.scheduled_fifo.ScheduledFIFO({'routing': 'round-robin', 'nbr_peers': 2})
        f.add_reader("r1")
        f.add_reader("r2")

        # Ensure fifo is empty
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r2")
        self.assertFalse(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(1, "r2"))

        # Add something
        self.assertTrue(f.write(Token('1')))
        self.assertTrue(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(1, "r2"))

        # Add something
        self.assertTrue(f.write(Token('2')))
        self.assertTrue(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(2, "r1"))
        self.assertTrue(f.tokens_available(1, "r2"))

        # Reader r2 read something
        self.verify_data(['2'], [f.peek('r2')])
        self.assertTrue(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(2, "r1"))
        self.assertFalse(f.tokens_available(1, "r2"))
        f.commit('r2')
        self.assertTrue(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(2, "r1"))
        self.assertFalse(f.tokens_available(1, "r2"))

        self.assertEquals([True] * 2, [f.write(Token(t)) for t in ['3', '4']])
        self.verify_data(['1', '3'], [f.peek('r1') for _ in range(2)])
        f.commit("r1")

        # Reader r1 all done, ensure reader r2 can still read
        self.assertTrue(f.tokens_available(1, "r2"))
        self.assertFalse(f.tokens_available(1, "r1"))

        # Reader r2 reads something
        self.verify_data(['4'], [f.peek("r2") for _ in range(1)])
        f.commit("r2")
        self.assertFalse(f.tokens_available(1, "r2"))

        self.assertTrue(f.write(Token('5')))
        self.verify_data(['5'], [f.peek("r1")])

        self.assertTrue(f.write(Token('6')))
        self.assertFalse(f.tokens_available(1, "r1"))
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertTrue(f.tokens_available(1, "r2"))
        self.verify_data(['6'], [f.peek("r2")])

        f.commit("r2")
        f.commit("r1")

        self.assertTrue(f.write(Token('7')))
        self.assertTrue(f.write(Token('8')))
        self.assertTrue(f.write(Token('9')))
        self.assertTrue(f.write(Token('10')))

        self.verify_data(['7', '9'], [f.peek("r1") for _ in range(2)])
        self.verify_data(['8', '10'], [f.peek("r2") for _ in range(2)])
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r2")

    def test_scheduled_queue_2(self):
        """Round-Robin scheduled queue test"""

        f = queue.scheduled_fifo.ScheduledFIFO({'routing': 'round-robin', 'nbr_peers': 2})
        f.add_reader("r1")
        f.add_reader("r2")

        # Ensure fifo is empty
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r2")
        self.assertFalse(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(1, "r2"))

        # Fill up
        self.assertEquals([True] * 4, [f.write(Token(t)) for t in map(lambda x: str(x), range(1,5))])
        self.assertTrue(f.tokens_available(2, "r1"))
        self.assertTrue(f.tokens_available(2, "r2"))

        # Reader r2 read something
        self.verify_data(['2'], [f.peek('r2')])
        self.assertFalse(f.tokens_available(2, "r2"))
        self.assertTrue(f.tokens_available(1, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))
        f.cancel('r2')
        self.assertTrue(f.tokens_available(2, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))

        # Reader r2 read something again
        self.verify_data(['2'], [f.peek('r2')])
        self.assertFalse(f.tokens_available(2, "r2"))
        self.assertTrue(f.tokens_available(1, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))
        f.cancel('r2')
        self.assertTrue(f.tokens_available(2, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))

        # Reader r2 read something again plus some
        self.verify_data(['2', '4'], [f.peek('r2') for _ in range(2)])
        self.assertFalse(f.tokens_available(1, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))
        f.cancel('r2')
        self.assertTrue(f.tokens_available(2, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))

        # Reader r2 read something again
        self.verify_data(['2', '4'], [f.peek('r2') for _ in range(2)])
        self.assertFalse(f.tokens_available(1, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))
        f.commit('r2')
        self.assertFalse(f.tokens_available(1, "r2"))
        self.assertTrue(f.tokens_available(2, "r1"))

        self.verify_data(['1', '3'], [f.peek('r1') for _ in range(2)])
        self.assertFalse(f.tokens_available(1, "r1"))
        f.commit('r1')
        self.assertFalse(f.tokens_available(1, "r1"))

    def test_scheduled_queue_3(self):
        """Round-Robin scheduled queue test"""

        f = queue.scheduled_fifo.ScheduledFIFO({'routing': 'round-robin', 'nbr_peers': 2})
        f.add_reader("r1")
        f.add_reader("r2")

        # Ensure fifo is empty
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r2")
        self.assertFalse(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(1, "r2"))

        count = {'r1': 0, 'r2': 0}
        values = {'r1': [], 'r2': []}

        for k in range(10):
            # Fill up
            self.assertEquals([True] * 4, [f.write(Token(t)) for t in map(lambda x: str(x), range(k*4+1,k*4+5))])

            # Empty
            for r in ['r1', 'r2']:
                while True:
                    try:
                        values[r].append(f.peek(r))
                        count[r] += 1
                    except queue.common.QueueEmpty:
                        break
                f.commit(r)
        assert count['r1'] == 20
        assert count['r2'] == 20
        values['r1'] = [int(v.value) for v in values['r1']]
        values['r2'] = [int(v.value) for v in values['r2']]
        # No common tokens and always in order
        assert len(set(values['r1']).intersection(set(values['r2']))) == 0
        assert sorted(values['r1']) == values['r1']
        assert sorted(values['r2']) == values['r2']

    def test_scheduled_queue_4(self):
        """Random scheduled queue test"""

        f = queue.scheduled_fifo.ScheduledFIFO({'routing': 'random', 'nbr_peers': 2})
        f.add_reader("r1")
        f.add_reader("r2")

        # Ensure fifo is empty
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r1")
        self.assertRaises(queue.common.QueueEmpty, f.peek, "r2")
        self.assertFalse(f.tokens_available(1, "r1"))
        self.assertFalse(f.tokens_available(1, "r2"))

        count = {'r1': 0, 'r2': 0}
        values = {'r1': [], 'r2': []}

        for k in range(10):
            # Fill up
            self.assertEquals([True] * 4, [f.write(Token(t)) for t in map(lambda x: str(x), range(k*4+1,k*4+5))])

            # Empty
            for r in ['r1', 'r2']:
                while True:
                    try:
                        values[r].append(f.peek(r))
                        count[r] += 1
                    except queue.common.QueueEmpty:
                        break
                f.commit(r)
        # Even if random assume that at least 5 tokens to each peer
        assert count['r1'] > 5
        assert count['r2'] > 5
        assert sum(count.values()) == 10 * 4
        values['r1'] = [int(v.value) for v in values['r1']]
        values['r2'] = [int(v.value) for v in values['r2']]
        # No common tokens and always in order
        assert len(set(values['r1']).intersection(set(values['r2']))) == 0
        assert sorted(values['r1']) == values['r1']
        assert sorted(values['r2']) == values['r2']
