# The MIT License (MIT)
#
# Copyright (c) 2013 Curtis Schlak
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import inspect

__all__ = ['on', 'when']

def on(param_name):
  def f(fn):
    dispatcher = Dispatcher(param_name, fn)
    return dispatcher
  return f


def when(param_type):
  def f(fn):
    frame = inspect.currentframe().f_back
    func_name = fn.func_name if 'func_name' in dir(fn) else fn.__name__
    dispatcher = frame.f_locals[func_name]
    if not isinstance(dispatcher, Dispatcher):
      dispatcher = dispatcher.dispatcher
    dispatcher.add_target(param_type, fn)
    def ff(*args, **kw):
      return dispatcher(*args, **kw)
    ff.dispatcher = dispatcher
    return ff
  return f


class Dispatcher(object):
  def __init__(self, param_name, fn):
    frame = inspect.currentframe().f_back.f_back
    top_level = frame.f_locals == frame.f_globals
    self.param_index = inspect.getargspec(fn).args.index(param_name)
    self.param_name = param_name
    self.targets = {}

  def __call__(self, *args, **kw):
    typ = args[self.param_index].__class__
    d = self.targets.get(typ)
    if d is not None:
      return d(*args, **kw)
    else:
      issub = issubclass
      t = self.targets
      ks = t.iterkeys()
      return [t[k](*args, **kw) for k in ks if issub(typ, k)]

  def add_target(self, typ, target):
    self.targets[typ] = target