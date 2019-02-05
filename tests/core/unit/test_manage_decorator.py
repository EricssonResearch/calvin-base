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
from calvin.actor.actor import manage

# @manage()                     # Manage every instance variable known upon completion of __init__
# @manage(include = [])         # Manage nothing
# @manage(include = [foo, bar]) # Manage self.foo and self.bar only. Equivalent to @manage([foo, bar])
# @manage(exclude = [foo, bar]) # Manage everything except self.foo and self.bar
# @manage(exclude = [])         # Same as @manage()
# @manage(<list>)               # Same as @manage(include = <list>)


class Base(object):

    def __init__(self):
        self._managed = set(('id', 'name'))


class Dummy(Base):

    def __init(self):
        super(Dummy, self).__init__()

    def init(self):
        self.foo = True
        self.bar = True


class ManageTests(unittest.TestCase):

    def setUp(self):
        self.d = Dummy()

    def tearDown(self):
        pass

    def test1(self):
        assert set(('id', 'name')) == self.d._managed

    def test2(self):
        manage(['xxx'])(self.d.init)()
        assert 'xxx' in self.d._managed

    def test3(self):
        incl = ['xxx', 'yyy']
        manage(incl)(self.d.init)()
        assert set(incl) <= self.d._managed

    def test4(self):
        manage(exclude=[])(self.d.init)()
        assert len(self.d._managed) == 4

    def test5(self):
        manage()(self.d.init)()
        assert len(self.d._managed) == 4

    def test6(self):
        manage(exclude=['foo'])(self.d.init)()
        assert len(self.d._managed) == 3

    def test7(self):
        manage(include=['foo'], exclude=['foo'])(self.d.init)()
        assert len(self.d._managed) == 3

    def test8(self):
        manage(include=['foo'], exclude=['foo'])(self.d.init)()
        assert self.d._managed == set(('id', 'name', 'foo'))

    def test9(self):
        manage(exclude=['id'])(self.d.init)()
        assert 'id' in self.d._managed

    def test10(self):
        manage(include=[])(self.d.init)()
        assert self.d._managed == set(('id', 'name'))



if __name__ == '__main__':
    unittest.main()
