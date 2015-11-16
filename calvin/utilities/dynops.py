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

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)

class PauseIteration(Exception):
    def __init__(self):
        super(PauseIteration, self).__init__()

class FailedElement(Exception):
    """ Used as an element indicating a failure
    """
    def __init__(self):
        super(FailedElement, self).__init__()

class DynOps(object):
    """
    Dynamic operations built around hiraki of iterables.
    Leafs typically async operations filling in values from responses.
    Root and down are lazy evaluated.
    
    This should be used as an iterable, but with the extra exception
    PauseIteration which indicate that the iterable is not finsihed but
    waiting for dynamic filled in elements at leafs. Set a callback
    with set_cb to get notification when new element potentially is available.
    """

    def __init__(self):
        super(DynOps, self).__init__()
        self._trigger = None
        self.infinite_set = False
        self.cb_args = []
        self.cb_kwargs = {}
        self.name = ""

    def set_name(self, name):
        self.name = name
        # To enable setting name inline return self, i.e. it = DynOps(..).set_name("name")
        return self

    def set_cb(self, trigger, *args, **kwargs):
        self.cb_args = args
        self.cb_kwargs = kwargs
        self._trigger = trigger

    def trig(self):
        if self._trigger:
            self._trigger(*self.cb_args, **self.cb_kwargs)

    def trigger_add(self, iters):
        for i in iters:
            if hasattr(i, 'set_cb'):
                i.set_cb(self.trig)

    def op(self):
        """ Needs to be overriden in subclasses to get anything done """
        raise StopIteration

    def __iter__(self):
        return self

    def next(self):
        return self.op()

    def __next__(self):
        return self.next()


class Union(DynOps):
    """ A Dynamic Operations Union set operation
        The union between all supplied iterables
    """

    def __init__(self, *iters):
        super(Union, self).__init__()
        # To allow lists etc to be arguments directly always take the iter
        self.iters = [iter(v) for v in iters]
        # If any iterators are infinite the union will be infinite
        self.infinite_set = any([True for v in self.iters if getattr(v, 'infinite_set', False)])
        self.set = []
        self.trigger_add(self.iters)
        self.final = False
        if self.infinite_set:
            self.trig()
            self.final = True
            return

    def op(self):
        if self.infinite_set:
            raise PauseIteration
        paused = False
        for v in self.iters:
            try:
                while True:
                    _log.debug("%s:next TRY iter:%s" % (self.__str__(), str(v)))
                    n = v.next()
                    if n not in self.set:
                        _log.debug("%s:next GOT NEW value:%s iter:%s" % (self.__str__(), str(n), str(v)))
                        self.set.append(n)
                        return n
            except PauseIteration:
                _log.debug("%s:next GOT PAUSE iter:%s" % (self.__str__(), str(v)))
                paused = True
            except StopIteration:
                _log.debug("%s:next GOT STOP iter:%s" % (self.__str__(), str(v)))
                pass
        if paused:
            _log.debug("%s:next RAISE PAUSE" % (self.__str__(), ))
            raise PauseIteration
        else:
            _log.debug("%s:next RAISE STOP" % (self.__str__(), ))
            self.final = True
            raise StopIteration

    def __str__(self):
        s = ""
        for i in self.iters:
            s += i.__str__() + ", "
        return "Union%s%s%s(%s)" % (("<" + self.name + ">") if self.name else "",
                                    "<Inf>" if self.infinite_set else "",
                                    "#" if self.final else "-", s[:-2])

class Intersection(DynOps):
    """ A Dynamic Operations Intersection set operation
        The intersection between all supplied iterables
    """

    def __init__(self, *iters):
        super(Intersection, self).__init__()
        # To allow lists etc to be arguments directly always take the iter
        # Drop iterators which are infinite since not limiting
        self.iters = [iter(v) for v in iters if not getattr(v, 'infinite_set', False)]
        self.set = set([])
        self.candidates = set([])
        self.drawn = {id(k): set([]) for k in self.iters}
        self.final = {id(k): False for k in self.iters}
        self.trigger_add(self.iters)
        self._final = False
        if len(self.iters) == 0 and len(iters) > 0:
            # We only had infinite iters we are infinite
            self.infinite_set = True
            self.trig()

    def op(self):
        if self.infinite_set:
            raise PauseIteration
        if self.candidates:
            e = self.candidates.pop()
            self.set.add(e)
            return e
        while True:
            active = False
            for v in self.iters:
                if not self.final[id(v)]:
                    try:
                        self.drawn[id(v)].add(v.next())
                        active = True
                    except PauseIteration:
                        pass
                    except StopIteration:
                        self.final[id(v)] = True
            # Current seen intersection
            self.candidates.update(set.intersection(*[v for v in self.drawn.values()]))
            # remove from individual iterables
            for v in self.drawn.values():
                v.difference_update(self.candidates)
            # Remove previously seen
            self.candidates.difference_update(self.set)
            if self.candidates:
                e = self.candidates.pop()
                self.set.add(e)
                return e
            if not active or all(self.final.values()):
                break
        if all([self.final[id(v)] for v in self.iters]):
            self._final = True
            raise StopIteration
        else:
            raise PauseIteration

    def __str__(self):
        s = ""
        for i in self.iters:
            s += i.__str__() + ", "
        return "Intersection%s%s%s(%s)" % (("<" + self.name + ">") if self.name else "",
                                           "<Inf>" if self.infinite_set else "",
                                           "#" if self._final else "-", s[:-2])


class Difference(DynOps):
    """ A Dynamic Operations Difference set operation
        The first iterable is the main set which the following iterables are removed from
    """

    def __init__(self, first, *iters):
        super(Difference, self).__init__()
        # To allow lists etc to be arguments directly always take the iter
        self.first = iter(first)
        if getattr(self.first.infinite_set, 'infinite_set', False):
            # TODO implemnetation of infinte set that we remove from. Negative set???
            raise NotImplemented
        self.iters = [iter(v) for v in iters]
        self.zero_set = any([True for v in self.iters if getattr(v, 'infinite_set', False)])
        self.trigger_add([self.first] + self.iters)
        self.set = []
        self.remove = set([])
        self.final = {id(k): False for k in self.iters}

    def op(self):
        _log.debug("%s.next()" % self.__str__())
        if self.zero_set:
            _log.debug("%s.next() REMOVE INFINITE" % self.__str__())
            raise StopIteration
        if all(self.final.values()):
            _log.debug("%s.next() REMOVE THESE %s" % (self.__str__(), str(self.remove)))
            # All remove values obtained just filter first
            # The first's exception are exposed
            while True:
                n = self.first.next()
                _log.debug("%s.next() = %s" % (self.__str__(), str(n)))
                if n not in self.remove:
                    self.remove.add(n)  # Enforce set behaviour 
                    _log.debug("%s.next() ACTUAL = %s" % (self.__str__(), str(n)))
                    return n
        paused = False
        for v in self.iters:
            try:
                while True:
                    self.remove.add(v.next())
            except PauseIteration:
                paused = True
            except StopIteration:
                self.final[id(v)] = True
        if paused:
            raise PauseIteration
        else:
            # Need to call ourself since while collecting removes can only raise PauseIteration
            return self.op()

    def __str__(self):
        s = ""
        for i in self.iters:
            s += i.__str__() + ", "
        return "Difference%s%s(first=%s, %s)" % (("<" + self.name + ">") if self.name else "", "<Inf>" if self.infinite_set else "", 
                                               self.first.__str__(), s[:-2])
        

class Map(DynOps):
    """ A Dynamic Operations Map operation
        Applies a map function to all supplied iterables
        When 'eager' kwarg is True it will calculate candidate values directly instead of lazyily
        The map function must take the output List dynamic iterable as first argument
        The second argument is a persistent dictionary (populated from the kwargs supplied when creating Map)
        The third argument is a list of booleans if respective iterable have reached the end, 
            any such iterable will have None elements
        The following params are *args or the exact same number of arguments as iterables supplied.
        The map function is allowed to raise StopIteration which will prematurely end the iteration.
    """
    @staticmethod
    def identity(out_iter, kwargs,final, *elems):
        if len(elems) > 1:
            out_iter.extend([tuple(*elems)])
        else:
            out_iter.append(elems[0])

    def __init__(self, func, *iters, **kwargs):
        super(Map, self).__init__()
        self.func = func or Map.identity
        self.eager = kwargs.pop('eager', False)
        self.kwargs = kwargs
        # To allow lists etc to be arguments directly always take the iter
        self.iters = [iter(v) for v in iters]
        self.drawn = {id(k): [] for k in self.iters}
        self.final = {id(k): False for k in self.iters}
        self.trigger_add(self.iters)
        self.out_iter = List()

    def get_kwargs(self):
        return self.kwargs

    def set_cb(self, trigger, *args, **kwargs):
        self.cb_args = args
        self.cb_kwargs = kwargs
        self._trigger = trigger
        # Also trigger when adding to out list (since could be async appended, e.g. by storage)
        self.out_iter.cb_args = args
        self.out_iter.cb_kwargs = kwargs
        self.out_iter._trigger = trigger

    def trig(self):
        _log.debug("Map%s(func=%s) trig BEGIN" % (("<" + self.name + ">") if self.name else "", self.func.__name__))
        if self.eager:
            # Execute map function until Stop- or PauseIteration exception
            try:
                while True:
                    self._op(True)
            except:
                pass
        _log.debug("Map%s(func=%s) trig ACT %s" % (("<" + self.name + ">") if self.name else "", self.func.__name__, self._trigger))
        if self._trigger:
            self._trigger(*self.cb_args, **self.cb_kwargs)

    def _op(self, eager=False):
        while True:
            active = False
            for v in self.iters:
                if not self.final[id(v)]:
                    try:
                        _log.debug("Map%s(func=%s) Next iter: %s" % (("<" + self.name + ">") if self.name else "", self.func.__name__, str(v)))
                        e = v.next()
                        _log.debug("Map%s(func=%s) Next in: %s" % (("<" + self.name + ">") if self.name else "", self.func.__name__, e))
                        self.drawn[id(v)].append(e)
                        active = True
                    except PauseIteration:
                        pass
                    except StopIteration:
                        self.final[id(v)] = True
            try:
                l = min([len(self.drawn[id(i)]) for i in self.iters if not self.final[id(i)]])
            except ValueError:
                l = 0
            _log.debug("Map%s(func=%s) Loop: %d, Final:%s" % (("<" + self.name + ">") if self.name else "", self.func.__name__, l, self.final.values()))
            # Execute map function l times
            for i in range(l):
                try:
                    self.func(self.out_iter, self.kwargs, [self.final[id(i)] for i in self.iters],
                              *[None if self.final[id(i)] else self.drawn[id(i)].pop(0) for i in self.iters])
                except StopIteration:
                    self.final = {id(k): True for k in self.iters}
            # If no more elements to apply map on, then one final map execution to allow the map function to finalize
            if all(self.final.values()):
                self.func(self.out_iter, self.kwargs, self.final.values(),
                          *([None]*len(self.iters)))
            # If lazy break out of while True with the return value (or exception) otherwise break when no progress
            if not eager:
                _log.debug("Map%s(func=%s) TRY OUT %s" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__, self.out_iter))
                try:
                    e = self.out_iter.next()
                except StopIteration:
                    _log.debug("Map%s(func=%s) GOT STOP" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__))
                    raise StopIteration
                except PauseIteration:
                    _log.debug("Map%s(func=%s) GOT PAUSE" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__))
                    raise PauseIteration
                _log.debug("Map%s(func=%s) GOT OUT %s" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__, e))
                return e
            if not active or all(self.final.values()):
                # Reach here only when eager, any exception will do to break loop in trig method
                raise Exception()

    def op(self):
        try:
            # Deliver any already mapped results
            return self.out_iter.next()
        except PauseIteration:
            # Try to get more results
            return self._op()

    def __str__(self):
        s = ""
        for i in self.iters:
            s += i.__str__() + ", "
        return "Map%s%s(func=%s, %s)" % (("<" + self.name + ">") if self.name else "",
                                        "#" if self.out_iter._final else "-",
                                        self.func.__name__, s[:-2])


class Chain(DynOps):
    """ A Dynamic Operations Chain iterable operation
        
    """

    def __init__(self, it):
        super(Chain, self).__init__()
        # To allow lists etc to be arguments directly always take the iter
        self.it = iter(it)
        _log.debug("Chain.__init__(%s)" % str(self.it))
        self.elem_it = iter([])
        self.trigger_add([self.it])

    def op(self):
        try:
            _log.debug("Chain%s.next() Try %s" % (("<" + self.name + ">") if self.name else "", str(self.elem_it)))
            e = self.elem_it.next()
            _log.debug("Chain%s.next()=%s" % ((("<" + self.name + ">") if self.name else "", str(e))))
            return e
        except StopIteration:
            _log.debug("Chain%s.next() ELEM ITER STOP %s" % (("<" + self.name + ">") if self.name else "", str(self.elem_it)))
            try:
                self.elem_it = self.it.next()
            except StopIteration:
                _log.debug("Chain%s.next() ITER STOP %s" % (("<" + self.name + ">") if self.name else "", str(self.it)))
                raise StopIteration
            except PauseIteration:
                _log.debug("Chain%s.next() ITER PAUSE %s" % (("<" + self.name + ">") if self.name else "", str(self.it)))
                raise PauseIteration
            except Exception as e:
                _log.debug("Chain%s.next() ITER OTHER EXCEPTION %s" % (("<" + self.name + ">") if self.name else "", str(self.it)), exc_info=True)
                raise e
            _log.debug("Chain%s.next() New iterator %s" % (("<" + self.name + ">") if self.name else "", str(self.elem_it)))
            # when not exception try to take next from the latest list
            return self.op()


    def __str__(self):
        return "Chain%s(%s)" % (("<" + self.name + ">") if self.name else "", self.it.__str__())

class List(DynOps):
    """ A Dynamic Operations List
        The list grows dynamically and will trigger higher set operations
        Optionally takes an initial list of elements, add elements
        by append or extend. Call final when no more elements will be added.
        Call auto_final and set a max length after which StopIteration is raised.
    """
    def __init__(self, elems=None):
        super(List, self).__init__()
        self.list = elems if elems else []
        self._final = False
        self.index = 0
        self.max_length = float("inf")

    def append(self, elem):
        _log.debug("%s.append(%s)" % (self.__str__(), elem))
        if not self._final:
            self.list.append(elem)
            # Potentially an interable
            self.trigger_add([elem])
            self.trig()

    def extend(self, elems):
        _log.debug("%s.extend(%s)" % (self.__str__(), elems))
        if not self._final:
            self.list.extend(elems)
            # Potentially an interable
            self.trigger_add(elems)
            self.trig()

    def final(self):
        if not self._final:
            self._final = True
            self.trig()

    def auto_final(self, max_length):
        _log.debug("%s:auto_final max:%d index:%d final:%s trigger:%s" % (self.__str__(), 
                        max_length, self.index, str(self._final), str(self._trigger)))
        self.max_length = max_length
        if self.index >= self.max_length:
            self.final()

    def op(self):
        if self.index >= self.max_length:
            self._final = True
            raise StopIteration
        try:
            e = self.list[self.index]
            _log.debug("%s.next() = %s" % (self.__str__(), e))
            self.index += 1
            return e
        except:
            if self._final:
                _log.debug("%s.next() GOT STOP" % self.__str__())
                raise StopIteration
            else:
                _log.debug("%s.next() GOT PAUSE" % self.__str__())
                raise PauseIteration

    def __str__(self):
        s = ""
        c = 0
        for i in self.list:
            s += "-> " if c==self.index else ""
            c += 1
            s += i.__str__() + ", "
        s = s[:-2]
        s += ">>>" if c==self.index else ""
        return "List%s%s(%s)" % (("<" + self.name + ">") if self.name else "", "#" if self._final else "-", s)


class Infinite(DynOps):
    """ A Dynamic Operations Infinite set
    """
    def __init__(self):
        super(Infinite, self).__init__()
        self.infinite_set = True

    def op(self):
        raise PauseIteration

    def __str__(self):
        return "Infinite%s()" % (("<" + self.name + ">") if self.name else "")

import pprint
if __name__ == '__main__':
    def gotit():
        print "Triggered"
        try:
            # print "INFINITE", d.infinite_set
            for i in d:
                print i
        except PauseIteration:
            print "Paused"

    l1 = List()
    def map_func(it, kwargs, final, *iters):
        if all(final):
            it.final()
        else:
            print kwargs, iters
            it.append(sum([0 if i is None else i for i in iters]) + kwargs['bias'])
            kwargs['bias'] += 10

    d = Map(map_func, l1, eager=True, bias=100)
    d.set_cb(gotit)
    l1.append(1)
    l1.extend([4,5,10,2,3])
    l1.final()

    """
    l1 = List()
    l2 = List()
    l3 = List()
    d = Union(l3, Difference(Intersection(l1, [1, 2, 3], [3, 2, 1], l2, Infinite()), l3))
    d.set_cb(gotit)
    l2.extend(1,2,3,4)
    l3.extend(2)
    l3.final()
    l2.extend(6,7,8,9)
    l2.final()
    l1.append(1)
    l1.extend(4,5,10,2,3)
    l1.final()

    #try:
    #    for i in d:
    #        print i
    #except PauseIteration:
    #    print "Paused 2"
    pprint.pprint(d.final)

    l1 = List()
    l2 = List()
    d = Union(l1, [1, 2, 3], ['a', 'b', 'c'], l2)
    l2.extend(1,2,3,4)
    try:
        for i in d:
            print i
    except PauseIteration:
        print "Paused"

    l2.extend(6,7,8,9)
    l2.final()
    l1.append(1)
    l1.extend(4,5,10)

    try:
        for i in d:
            print i
    except PauseIteration:
        print "Paused"

    l1.final()

    try:
        for i in d:
            print i
    except PauseIteration:
        print "Paused"
    """