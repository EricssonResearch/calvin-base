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

import unittest
from calvin.runtime.north import fifo
from calvin.runtime.north.calvin_token import Token


class FifoTests(unittest.TestCase):

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
        f = fifo.FIFO(5)
        f.add_reader('p1.id')
        data = ['1', '2', '3', '4']
        for token in data:
            self.assertTrue(f.can_write())
            self.assertTrue(f.write(Token(token)))

        self.verify_data(['1', '2'], [f.read('p1.id') for _ in range(2)])

        f.commit_reads('p1.id', True)
        f.add_reader('p1.id')

        self.verify_data(['3', '4'], [f.read('p1.id') for _ in range(2)])

        self.assertEquals(None, f.read('p1.id'))

        f.commit_reads('p1.id', True)

        for token in ['5', '6', '7', '8']:
            self.assertTrue(f.can_write())
            self.assertTrue(f.write(Token(token)))

        self.assertFalse(f.can_write())

        self.verify_data(['5', '6', '7', '8'], [f.read('p1.id')
                                                for _ in range(4)])
        f.commit_reads('p1.id', True)

    def test2(self):
        """Multiple readers"""

        f = fifo.FIFO(5)
        f.add_reader("r1")
        f.add_reader("r2")

        # Ensure fifo is empty
        self.assertEquals(f.read("r1"), None)
        self.assertEquals(len(f), 0)

        # Add something
        self.assertTrue(f.write(Token('1')))
        self.assertEquals(len(f), 1)

        # Reader r1 read something
        self.assertTrue(f.read('r1'))
        f.commit_reads('r1')

        self.assertEquals([True] * 3, [f.write(Token(t)) for t in ['2', '3', '4']])
        self.assertFalse(f.write(Token('5')))
        self.verify_data(['2', '3', '4'], [f.read('r1') for _ in range(3)])
        f.commit_reads("r1")

        # Reader r1 all done, ensure reader r2 can still read
        self.assertEquals(len(f), 4)
        self.assertFalse(f.can_write())
        self.assertTrue(f.can_read("r2"))
        self.assertFalse(f.can_read("r1"))

        # Reader r2 reads something
        self.verify_data(['1', '2', '3'], [f.read("r2") for _ in range(3)])
        f.commit_reads("r2")
        self.assertEquals(len(f), 1)

        self.assertTrue(f.write(Token('5')))
        self.verify_data(['4', '5'], [f.read("r2") for _ in range(2)])

        self.assertFalse(f.can_read("r2"))
        self.assertEquals(None, f.read("r2"))
        self.assertTrue(f.can_read("r1"))
        self.verify_data(['5'], [f.read("r1")])

        f.commit_reads("r2")
        f.commit_reads("r1")

        self.assertTrue(f.write(Token('6')))
        self.assertTrue(f.write(Token('7')))
        self.assertTrue(f.write(Token('8')))

        self.assertTrue([f.read("r1")
                         for _ in range(4)], [f.read("r2") for _ in range(4)])

    def test3(self):
        """Testing commit reads"""
        f = fifo.FIFO(5)
        f.add_reader("r1")

        for token in ['1', '2', '3', '4']:
            self.assertTrue(f.can_write())
            self.assertTrue(f.write(Token(token)))

        # Fails, fifo full
        self.assertFalse(f.can_write())
        self.assertFalse(f.write(Token('5')))

        # Tentative, fifo still full
        self.verify_data(['1'], [f.read("r1")])
        self.assertFalse(f.can_write())
        self.assertFalse(f.write(Token('5')))

        # commit previous reads, fifo 1 pos free
        f.commit_reads('r1')
        self.assertTrue(f.can_write())
        self.assertTrue(f.write(Token('5')))
        # fifo full again
        self.assertFalse(f.can_write())
        self.assertFalse(f.write(Token('5')))

    def test4(self):
        """Testing rollback reads"""
        f = fifo.FIFO(5)
        f.add_reader('r1')

        for token in ['1', '2', '3', '4']:
            self.assertTrue(f.can_write())
            self.assertTrue(f.write(Token(token)))

        # fifo full
        self.assertFalse(f.can_write())
        self.assertFalse(f.write(Token('5')))

        # tentative reads
        self.verify_data(['1', '2', '3', '4'], [f.read("r1")
                                                for _ in range(4)])
        # len unchanged
        self.assertEquals(len(f), 4)

        f.rollback_reads("r1")
        self.assertFalse(f.can_write())
        self.assertFalse(f.write(Token('5')))
        self.assertEquals(len(f), 4)

        # re-read
        self.verify_data(['1'], [f.read("r1")])
        f.commit_reads("r1")
        self.assertEquals(len(f), 3)

        # one pos free in fifo
        self.assertTrue(f.can_write())
        self.assertTrue(f.write(Token('a')))
        self.assertFalse(f.can_write())
        self.assertFalse(f.write(Token('b')))
