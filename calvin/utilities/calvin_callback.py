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

from calvin.utilities import calvinuuid
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


class CalvinCB(object):
    """ This is calvins generic function caller used in callbacks etc.
        func: the function that will be called
        args: any positional arguments specific for this callback
        kwargs: any key-value arguments specific for this callback

        For example see example code at end of file.
    """
    def __init__(self, func, *args, **kwargs):
        super(CalvinCB, self).__init__()
        self.id = calvinuuid.uuid("CB")
        self.func = func
        self.args = list(args)
        self.kwargs = kwargs
        # Ref a functions name if we wrap several CalvinCB and need to take __str__
        try:
            self.name = self.func.__name__
        except:
            self.name = self.func.name if hasattr(self.func, 'name') else "unknown"

    def args_append(self, *args):
        """ Append specific args to the call"""
        self.args.append(*args)

    def kwargs_update(self, **kwargs):
        """ Update specific kwargs to the call"""
        self.kwargs.update(kwargs)

    def __call__(self, *args, **kwargs):
        """ Call function
            args: any positional arguments for this call of the callback
            kwargs: any key-value arguments for this call of the callback

            returns the callbacks return value when no exception
        """
        try:
            return self.func(*(self.args + list(args)), **dict(self.kwargs, **kwargs))
        except:
            _log.exception("When callback %s %s(%s, %s) is called caught the exception" % (
                self.func, self.func.__name__, (self.args + list(args)), dict(self.kwargs, **kwargs)))

    def __str__(self):
        return "CalvinCB - " + self.name + "(%s, %s)" % (self.args, self.kwargs)


class CalvinCBGroup(object):
    """ A group of callbacks that will have some common args
        funcs: a list of callbacks of CalvinCB type

        For example see example code at end of file.
    """
    def __init__(self, funcs=None):
        super(CalvinCBGroup, self).__init__()
        self.id = calvinuuid.uuid("CBG")
        self.funcs = funcs if funcs else []

    def func_append(self, func):
        """ Add CalvinCB instances to be called"""
        self.funcs.append(func)

    def __call__(self, *args, **kwargs):
        """ Call functions
            args: any positional arguments for this call of the callbacks
            kwargs: any key-value arguments for this call of the callbacks

            returns a dictionary of the individual callbacks return value, with callback id as key.
        """
        reply = {}
        for f in self.funcs:
            reply[f.id] = f(*args, **kwargs)
        return reply


class CalvinCBClass(object):
    """ Callback class that handles named sets of callbacks
        that outside users can register callbacks for. The class
        is inherited by another class to add callback support.

        callbacks: a dictionary of names with list of callbacks
                   {'n1': [cb1, cb2], ...}
                   cb1, cb2 is CalvinCB or CalvinCBGroup type

        callback_valid_names: None or a list of strings setting the
                   valid names of callbacks, when None all names allowed
                   when list all non-matching names will be dropped during
                   registering.

        For example see example code at end of file.
    """
    def __init__(self, callbacks=None, callback_valid_names=None):
        self.__callbacks = {}
        self.__callback_valid_names = callback_valid_names
        if not callbacks:
            return
        for name, cbs in callbacks.iteritems():
            if self.__callback_valid_names is None or name in self.__callback_valid_names:
                self.__callbacks[name] = dict([(cb.id, cb) for cb in cbs])

    def callback_valid_names(self):
        """ Returns list of valid or current names that callbacks can be registered on."""
        return self.__callback_valid_names if self.__callback_valid_names else self.__callbacks.keys()

    def callback_register(self, name, cb):
        """ Registers a callback on a name.
            name: a name string
            cb: a callback of CalvinCB or CalvinCBGroup type
        """
        if self.__callback_valid_names is None or name in self.__callback_valid_names:
            if name not in self.__callbacks:
                self.__callbacks[name] = {}
            self.__callbacks[name][cb.id] = cb

    def callback_unregister(self, _id):
        """ Unregisters a callback
            _id: the id of the callback to unregister (CalvinCB and CalvinCBGroup have an attribute id)
        """
        for k, v in self.__callbacks.iteritems():
            if _id in v:
                self.__callbacks[k].pop(_id)
                if not self.__callbacks[k]:
                    del self.__callbacks[k]
                break

    def _callback_execute(self, name, *args, **kwargs):
        """ Will execute the callbacks registered for the name
            name: a name string
            args: any positional arguments for this call of the callbacks
            kwargs: any key-value arguments for this call of the callbacks

            returns a dictionary of the individual callbacks return value, with callback id as key.
        """
        reply = {}

        if name not in self.__callbacks:
            _log.debug("No callback registered for '%s'" % name)
            # tb_str = ''
            # for a in traceback.format_stack(limit=10)[:-1]:
            #     tb_str += a
            # _log.debug('\n' + tb_str)
            return reply

        # So we can change __callbacks from callbacks
        local_copy = self.__callbacks[name].copy()
        for cb in local_copy.itervalues():
            try:
                reply[cb.id] = cb(*args, **kwargs)
            except:
                _log.exception("Callback '%s' failed on %s(%s, %s)" % (name, cb, args, kwargs))
        return reply


if __name__ == '__main__':
    def fname(arg1, arg2, kwarg1):
        """docstring for fname"""
        print "Jippie", arg1, "/", arg2, "/", kwarg1
        return True

    def fname2(arg2, kwarg1):
        """docstring for fname"""
        print "Jippie2", arg2, "/", kwarg1
        return True

    def fname3(arg2, kwarg1):
        """docstring for fname"""
        raise Exception("Buuuu!")
        return True

    a = CalvinCB(fname, 1)
    a(10, kwarg1=2)
    a(20, kwarg1=3)

    print "------------------"

    b = CalvinCBGroup([CalvinCB(fname, 2000)])
    b.func_append(CalvinCB(fname, 2))
    b.func_append(CalvinCB(fname3))
    b.func_append(CalvinCB(fname2))
    b(50, kwarg1=10)

    class TestingCB(CalvinCBClass):
        """docstring for Testing"""
        def __init__(self, arg, callbacks=None):
            super(TestingCB, self).__init__(callbacks, ["test1", "test2"])
            self.arg = arg

        def internal(self):
            """docstring for fname"""
            print "------------------"
            print ">>>", self._callback_execute("test1", 100, kwarg1=12)
            print "------------------"
            print ">>>", self._callback_execute("test2", 500, kwarg1=13)

    t = TestingCB(1, callbacks={'test1': [a], 'test2': [b]})
    t.callback_register('test1', CalvinCB(fname2))
    t.callback_unregister(a.id)
    print t.callback_valid_names()
    t.internal()
