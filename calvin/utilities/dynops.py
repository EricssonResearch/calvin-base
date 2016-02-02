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

import random

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

    def __str__(self):
        return "FailedElement"

class FinalElement(Exception):
    """ Used as an element indicating reached end, only used during special circumstances
    """
    def __init__(self):
        super(FinalElement, self).__init__()

    def __str__(self):
        return "FinalElement"

class InfiniteElement(Exception):
    """ Used as an element indicating that the set drawn from is infinite
    """
    def __init__(self):
        super(InfiniteElement, self).__init__()

    def __str__(self):
        return "InfiniteElement"


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
        self.infinite_sent = False
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

    def miss_cb_str(self):
        return "" if self._trigger else "<NoCB>" 

    def trig(self):
        _log.debug("%s TRIG BEGIN" % (self.__str__()))
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
        if self.infinite_set:
            _log.debug("%s INFINITE" % self.__str__())
            if self.infinite_sent:
                _log.debug("%s INFINITE STOP" % self.__str__())
                raise StopIteration
            else:
                _log.debug("%s INFINITE SEND" % self.__str__())
                self.infinite_sent = True
                # FIXME Need to trig?
                #self.trig()
                return InfiniteElement
        return self.op()

    def __next__(self):
        return self.next()

    def __repr__(self):
        # Force to use the str, good e.g. when adding tuple elements for Collect.
        # Since otherwise it is just stating an instance of ...
        return self.__str__()


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
            sub = i.__str__()
            for line in sub.splitlines():
                s += "\n\t" + line
            s += ", "
        return "Union%s%s%s%s(%s\n)" % (("<" + self.name + ">") if self.name else "",
                                    "<Inf>" if self.infinite_set else "",
                                    "#" if self.final else "-", self.miss_cb_str(), s[:-2])

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
        self.infs = {id(k): False for k in self.iters}
        self.trigger_add(self.iters)
        self._final = False
        if len(self.iters) == 0 and len(iters) > 0:
            # We only had infinite iters we are infinite
            self.infinite_set = True
            self.trig()

    def op(self):
        if self.candidates:
            e = self.candidates.pop()
            self.set.add(e)
            return e
        while True:
            active = False
            for v in self.iters:
                if not self.final[id(v)]:
                    try:
                        n = v.next()
                        if isinstance(n, InfiniteElement):
                            self.infs[id(v)] = True
                            self.final[id(v)] = True
                        self.drawn[id(v)].add(n)
                        active = True
                    except PauseIteration:
                        pass
                    except StopIteration:
                        self.final[id(v)] = True
            if all(self.infs.values()):
                self.infinite_set = True
                if self.infinite_sent:
                    _log.debug("%s INFINITE STOP" % self.__str__())
                    raise StopIteration
                else:
                    _log.debug("%s INFINITE SEND" % self.__str__())
                    self.infinite_sent = True
                    # FIXME Need to trig?
                    #self.trig()
                    return InfiniteElement
                
            # Current seen intersection
            self.candidates.update(set.intersection(*[self.drawn[id(v)] for v in self.iters if not self.infs[id(v)]]))
            _log.debug("Intersection%s%s%s candidates: %s drawn: %s infs: %s"  % (("<" + self.name + ">") if self.name else "",
                                           "<Inf>" if self.infinite_set else "",
                                           "#" if self._final else "-", self.candidates, self.drawn.values(), self.infs.values()))
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
            sub = i.__str__()
            for line in sub.splitlines():
                s += "\n\t" + line
            s += ", "
        return "Intersection%s%s%s%s(%s\n) out=%s, candidates=%s" % (("<" + self.name + ">") if self.name else "",
                                           "<Inf>" if self.infinite_set else "",
                                           "#" if self._final else "-", self.miss_cb_str(), s[:-2], self.set, self.candidates)


class Difference(DynOps):
    """ A Dynamic Operations Difference set operation
        The first iterable is the main set which the following iterables are removed from
    """

    def __init__(self, first, *iters):
        super(Difference, self).__init__()
        # To allow lists etc to be arguments directly always take the iter
        self.first = iter(first)
        if getattr(self.first.infinite_set, 'infinite_set', False):
            # TODO implementation of infinite set that we remove from. Negative set???
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
            sub = i.__str__()
            for line in sub.splitlines():
                s += "\n\t" + line
            s += ", "
        f = ""
        sub = self.first.__str__()
        for line in sub.splitlines():
            f += "\n\t" + line
        return "Difference%s%s%s(first=%s, %s\n)" % (("<" + self.name + ">") if self.name else "", "<Inf>" if self.infinite_set else "", 
                                               f, self.miss_cb_str(), s[:-2])
        

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
        self.during_next = False

    def get_kwargs(self):
        return self.kwargs

    def out_trig(self):
        if not self.during_next:
            self.trig()

    def set_cb(self, trigger, *args, **kwargs):
        self.cb_args = args
        self.cb_kwargs = kwargs
        self._trigger = trigger
        # Also trigger when adding to out list (since could be async appended, e.g. by storage)
        self.out_iter._trigger = self.out_trig

    def trig(self):
        _log.debug("%s trig BEGIN" % (self.__str__()))
        if self.eager:
            # Execute map function until Stop- or PauseIteration exception
            try:
                while True:
                    self._op(True)
            except:
                pass
        if self._trigger:
            self._trigger(*self.cb_args, **self.cb_kwargs)

    def _op(self, eager=False):
        self.during_next = True
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
                    except Exception as e:
                        _log.exception("Map function failed")
                        raise e
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
                except PauseIteration:
                    break
                except StopIteration:
                    self.final = {id(k): True for k in self.iters}
                except Exception as e:
                    _log.exception("Map function failed")
                    raise e
            # If no more elements to apply map on, then one final map execution to allow the map function to finalize
            if all(self.final.values()):
                try:
                    self.func(self.out_iter, self.kwargs, self.final.values(),
                              *([None]*len(self.iters)))
                except PauseIteration:
                    pass
                except StopIteration:
                    pass
                except Exception as e:
                    _log.exception("Map function failed")
                    raise e
            # If lazy break out of while True with the return value (or exception) otherwise break when no progress
            if not eager:
                _log.debug("Map%s(func=%s) TRY OUT %s" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__, self.out_iter))
                try:
                    e = self.out_iter.next()
                except StopIteration:
                    _log.debug("Map%s(func=%s) GOT STOP" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__))
                    self.during_next = False
                    raise StopIteration
                except PauseIteration:
                    _log.debug("Map%s(func=%s) GOT PAUSE" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__))
                    self.during_next = False
                    raise PauseIteration
                _log.debug("Map%s(func=%s) GOT OUT %s" % (("<" + self.name + ">") if self.name else "", 
                                                         self.func.__name__, e))
                self.during_next = False
                return e
            if not active or all(self.final.values()):
                # Reach here only when eager, any exception will do to break loop in trig method
                self.during_next = False
                raise Exception()

    def op(self):
        self.during_next = True
        try:
            # Deliver any already mapped results
            n = self.out_iter.next()
            self.during_next = False
            return n
        except PauseIteration:
            # Try to get more results
            return self._op()

    def __str__(self):
        s = ""
        for i in self.iters:
            sub = i.__str__()
            for line in sub.splitlines():
                s += "\n\t" + line
            s += ", "
        return "Map%s%s%s(func=%s, %s\n) out=%s" % (("<" + self.name + ">") if self.name else "",
                                        "#" if self.out_iter._final else "-", self.miss_cb_str(),
                                        self.func.__name__, s[:-2], self.out_iter.__str__())


class Chain(DynOps):
    """ A Dynamic Operations Chain iterable operation
        
    """

    def __init__(self, it):
        super(Chain, self).__init__()
        # To allow lists etc to be arguments directly always take the iter
        self.it = iter(it)
        _log.debug("%s.__init__()" % self.__str__())
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
        f = ""
        sub = self.it.__str__()
        for line in sub.splitlines():
            f += "\n\t" + line
        return "Chain%s%s(%s\n)" % (("<" + self.name + ">") if self.name else "", self.miss_cb_str(), f)

class Collect(DynOps):
    """ A Dynamic Operations Collect iterable operation
        Collect iterables into one iterable unordered,
        with optional tuple (key, value) for each value
    """

    def __init__(self, it, keyed=True):
        super(Collect, self).__init__()
        # To allow lists etc to be arguments directly always take the iter
        self.it = iter(it)
        self.it_final = False
        self.keyed = keyed
        self.iters = []
        self.trigger_add([self.it])

    def fill_iters(self):
        if self.it_final:
            return
        while True:
            try:
                self.iters.append(self.it.next())
            except StopIteration:
                self.it_final = True
                break
            except:
                break

    def op(self):
        # Fill up with any new iterables
        self.fill_iters()
        if self.it_final and not self.iters:
            # Done
            raise StopIteration
        # Make shuffled copy of iterables, need copy anyway due to iters modification inside loop
        iters_copy = self.iters
        random.shuffle(iters_copy)
        for elem in iters_copy:
            key, it = elem if self.keyed else (None, elem)
            try:
                e = it.next()
                return (key, e) if self.keyed else e
            except PauseIteration:
                continue
            except StopIteration:
                self.iters.remove(elem)
                continue
        raise PauseIteration


    def __str__(self):
        f = ""
        sub = self.it.__str__()
        for line in sub.splitlines():
            f += "\n\t" + line
        return "Collect%s%s(%s\n)" % (("<" + self.name + ">") if self.name else "", self.miss_cb_str(), f)


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

    def append(self, elem, trigger_iter=None):
        """ Append elem to dynamic list
            Optinally specify what dynops iterable should trigger this instance
            this is useful when having (key, iter) tuples for Collect
        """
        _log.debug("%s.append(%s)" % (self.__str__(), elem))
        if not self._final:
            self.list.append(elem)
            # Potentially an interable
            self.trigger_add([trigger_iter if trigger_iter else elem])
            self.trig()

    def extend(self, elems, trigger_iters=None):
        """ Extend elems to dynamic list
            Optinally specify what dynops iterables should trigger this instance
            this is useful when having (key, iter) tuples for Collect
        """
        _log.debug("%s.extend(%s)" % (self.__str__(), elems))
        if not self._final:
            self.list.extend(elems)
            # Potentially an interable
            self.trigger_add(trigger_iters if trigger_iters else elems)
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
            sub = i.__str__()
            p = True
            for line in sub.splitlines():
                s += "\n\t-> " if c==self.index and p else "\n\t   "
                p = False
                s += line
            s += ", "
            c += 1
        s = s[:-2]
        s += ">>>" if c==self.index else ""
        return "List%s%s%s(%s\n)" % (("<" + self.name + ">") if self.name else "", "#" if self._final else "-", 
                                    self.miss_cb_str(), s)


class Infinite(DynOps):
    """ A Dynamic Operations Infinite set
    """
    def __init__(self):
        super(Infinite, self).__init__()
        self.infinite_set = True

    def op(self):
        raise StopIteration

    def __str__(self):
        return "Infinite%s%s()" % (("<" + self.name + ">") if self.name else "", self.miss_cb_str(), )

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