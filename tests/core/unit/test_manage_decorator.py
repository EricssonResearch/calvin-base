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


@pytest.fixture
def dummy_actor():
    """Return actor with inherited _managed set, and properties foo and bar"""
    return Dummy()
            

def test1(dummy_actor):
    assert set(('id', 'name')) == dummy_actor._managed

def test2(dummy_actor):
    manage(['xxx'])(dummy_actor.init)()
    assert 'xxx' in dummy_actor._managed

def test3(dummy_actor):
    incl = ['xxx', 'yyy']
    manage(incl)(dummy_actor.init)()
    assert set(incl) <= dummy_actor._managed

def test4(dummy_actor):
    manage(exclude=[])(dummy_actor.init)()
    assert len(dummy_actor._managed) == 4

def test5(dummy_actor):
    manage()(dummy_actor.init)()
    assert len(dummy_actor._managed) == 4

def test6(dummy_actor):
    manage(exclude=['foo'])(dummy_actor.init)()
    assert len(dummy_actor._managed) == 3

def test7(dummy_actor):
    manage(include=['foo'], exclude=['foo'])(dummy_actor.init)()
    assert len(dummy_actor._managed) == 3

def test8(dummy_actor):
    manage(include=['foo'], exclude=['foo'])(dummy_actor.init)()
    assert dummy_actor._managed == set(('id', 'name', 'foo'))

def test9(dummy_actor):
    manage(exclude=['id'])(dummy_actor.init)()
    assert 'id' in dummy_actor._managed

def test10(dummy_actor):
    manage(include=[])(dummy_actor.init)()
    assert dummy_actor._managed == set(('id', 'name'))

